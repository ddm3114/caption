
import torch
import os 
import pandas as pd 
import numpy as np
import inspect
import flask
import json
import threading
import argparse
import construct.construct_utils
import construct.construct_redis_service
import time
from utils import base642Pil, initialize_logger
import sys
import os
current_path = os.path.abspath(__file__)
parent_directory = os.path.dirname(current_path)
print(parent_directory+'/MoE-LLaVA')
sys.path.append(parent_directory+'/MoE-LLaVA')

from moellava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from moellava.conversation import conv_templates, SeparatorStyle
from moellava.model.builder import load_pretrained_model
from moellava.utils import disable_torch_init
from moellava.mm_utils import tokenizer_image_token, get_model_name_from_path, KeywordsStoppingCriteria




api = flask.Flask(__name__)

lock = threading.Lock()
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=5001)
parser.add_argument("--dev", action="store_true", default=False)
parser.add_argument("--model_dir",type=str,default='/mnt/Devin')
args = parser.parse_args()



model_dir = args.model_dir 
model_path = os.path.join(model_dir, 'MoE-LLaVA-StableLM-1.6B-4e')

disable_torch_init()

device = 'cuda'
load_4bit, load_8bit = False, False
model_name = get_model_name_from_path(model_path)
tokenizer, model, processor, context_len = load_pretrained_model(model_path, None, model_name, load_8bit, load_4bit, device=device)


image_processor = processor['image']
conv_mode = "phi"  # phi or qwen or stablelm
conv = conv_templates[conv_mode].copy()
roles = conv.roles
image = 'moellava/serve/examples/WechatIMG4.jpg'
inp = 'Describe the image.'
inp = DEFAULT_IMAGE_TOKEN + '\n' + inp
conv.append_message(conv.roles[0], inp)
conv.append_message(conv.roles[1], None)
prompt = conv.get_prompt()
input_id = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()
stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
keywords = [stop_str]
stopping_criteria = KeywordsStoppingCriteria(keywords, tokenizer, input_id)

def inference(image):
    image_tensor = image_processor.preprocess(image, return_tensors='pt')['pixel_values'].to(model.device, dtype=torch.float16)
    
    with torch.inference_mode():
        output_ids = model.generate(
            input_id,
            images=image_tensor,
            do_sample=True,
            temperature=0.2,
            max_new_tokens=512,
            use_cache=True,
            stopping_criteria=[stopping_criteria],
            pad_token_id = 100257,
            eos_token_id = 100257
            )

    return output_ids





@api.route('/aliceImgCaption_api',methods=['POST'])
def imgCaption():
    app_log.info("### Mode: Image Caption ###\n")
    #try:
    reqs = flask.request.json.get('request')
    uids = []
    imgs = []

    total_start_time = time.time()
    
    
    for req in reqs:
        uids.append(req['uid'])
        params = req['params']
        imgs.append(params['img']) #base64
    
    imgs_process= []
    start_time = time.time()
    for img in imgs:
        img = base642Pil(img)
        if img.mode != "RGB":
            img = img.convert(mode="RGB")
        imgs_process.append(img)
    base642pil_time = time.time() - start_time

    start_time = time.time()
    preds = []
    for img in imgs_process:
        output_ids = inference(img)
        pred = tokenizer.decode(output_ids[0, input_id.shape[1]:], skip_special_tokens=True).strip()
        preds.append(pred)

   
    res = []

    for uid, pred in zip(uids, preds):
        tmp = {}
        tmp['params'] = {}
        tmp['uid'] = uid
        tmp['params']['caption'] = pred 
        app_log.info('Uid: {}'.format(uid)) 
        app_log.info('Image Caption: {}'.format(preds)) 
        res.append(tmp)
    
    caption_time = time.time() - start_time
    
    
    # 计算平均每张图的处理时间, 写入日志gi
    elapsed_time = time.time() - total_start_time
    avg_processing_time = elapsed_time / len(imgs)
    avg_base642pil_time = base642pil_time / len(imgs)
    avg_caption_time = caption_time / len(imgs) 
    
    
    
    app_log.info("Average Caption time per image: {:.4f} seconds".format(avg_caption_time))
    app_log.info("Average Base642PIL time per image: {:.4f} seconds".format(avg_base642pil_time))
    app_log.info("Average Processing time per image: {:.4f} seconds".format(avg_processing_time))

        
    return json.dumps({'result': res, 'success': True, "error_msg": ""})



def report_self_alive(redis_obj, server_addr, dev):
    try:
        now_time = int(time.time())
        batch_size = 1
        core_key_cap = "{aigc_img_caption}"
        core_keys = [core_key_cap]
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
