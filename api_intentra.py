
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os 
import pandas as pd 
import numpy as np
from transformers import pipeline
from transformers import AutoModelForTokenClassification, AutoTokenizer, TokenClassificationPipeline, VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
from peft import PeftModel
import inspect
import flask
import json
import threading
import argparse
import construct.construct_utils
import construct.construct_redis_service
import time
from utils import base642Pil, initialize_logger


api = flask.Flask(__name__)

lock = threading.Lock()
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=5001)
parser.add_argument("--dev", action="store_true", default=False)
parser.add_argument("--model_dir", type=str, default='/data/img_intent/files')
args = parser.parse_args()


# TinyLlama Model Initialization
stage_one_model_save_name = f'{args.model_dir}/intent_stage_one_model'
stage_two_model_save_name = f'{args.model_dir}/intent_stage_two_model'

MODEL_NAME = f'{args.model_dir}/TinyLlama-1.1B-intermediate-step-1431k-3T'
base_model1=AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    trust_remote_code=True,
    )

stage_one_model = PeftModel.from_pretrained(base_model1, stage_one_model_save_name)
stage_one_model = stage_one_model.merge_and_unload()
stage_one_tokenizer = AutoTokenizer.from_pretrained(stage_one_model_save_name, trust_remote_code=True)
stage_one_model.pad_token_id = stage_one_tokenizer.pad_token_id
stage_one_model.config.pad_token_id = stage_one_tokenizer.pad_token_id

stage_one_pipe = pipeline(task="text-generation", model=stage_one_model, tokenizer=stage_one_tokenizer, max_new_tokens=1, return_full_text=False)



@api.route('/classify_intent_round_one', methods=['POST'])
def intent_stage_one():
    data = flask.request.json.get('request')
    results = []
    success = True
    error_msg = None
    
    try:
        for req in data:
            uid = req['uid']
            params = req['params']
            app_log.info('**** Stage One Intent Api')
            app_log.info('Input Prompt: {}'.format(params['prompt']))
            outputs = stage_one_pipe(params['prompt'])
            sub_res = {'uid': uid,
                'params': {'intent': outputs[0]["generated_text"]}}
            app_log.info('Return Intent: {}'.format(outputs[0]["generated_text"]))
            results.append(sub_res)
    
    except Exception as e:
        error_msg = str(e)
        
    if error_msg:
        success = False
        
    output = {'result':results, 'success':success, 'error_msg': 'Stage One Intent Api: {}'.format(error_msg)}
    return json.dumps(output)




def report_self_alive(redis_obj, server_addr, dev):
    try:
        now_time = int(time.time())
        batch_size = 1
        core_key_intent_ra = "{aigc_imgintent_ra}"
        
        
        core_keys = [core_key_intent_ra]
        for core_key in core_keys:
            redis_obj.hset(core_key + "_info", server_addr, json.dumps({"batch_size": batch_size}))
            redis_obj.hset(core_key + "_heart_beat", server_addr, now_time)
            construct.construct_redis_service.ConstructRedis.clear(dev=dev, key=core_key[1:len(core_key)-1])
    except Exception as e:
        app_log.error("report_self_alive error:{}".format(e))

def init_sentry(port, dev):
    server_ip = construct.construct_utils.get_my_ip()
    server_addr = '{}:{}'.format(server_ip, port)

    def sentry_process(serve_addr: str):
        redis_obj = construct.construct_redis_service.ConstructRedis.get_redis_obj()
        time.sleep(1)
        report_self_alive(redis_obj, serve_addr, dev)
        while True:
            time.sleep(5)
            report_self_alive(redis_obj, serve_addr, dev)

    p = threading.Thread(target=sentry_process, args=(server_addr,), daemon=True)
    p.start()


if __name__ == '__main__':
    
    app_log = initialize_logger()
    construct.construct_redis_service.ConstructRedis.init_redis_db(dev=args.dev)
    redis_obj = construct.construct_redis_service.ConstructRedis.get_redis_obj()
    app_log.info(redis_obj)
    init_sentry(args.port, args.dev)    
    api.run(port=args.port,host='0.0.0.0') # 启动服务
