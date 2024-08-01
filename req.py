
import requests
import base64
from PIL import Image
from io import BytesIO
import time
import json

import base64
from PIL import Image
from io import BytesIO
# from diffusers import StableDiffusionPipeline, DDIMScheduler, EulerAncestralDiscreteScheduler
import random
import torch
import json
import inspect



# 发送请求并保存结果
results = []
image_count = 0  # 统计图片数量
start_time = time.time()  # 开始时间





stage_one_prompt = '''For the given conversation, please determine if you will send a picture to me. You will provide your answer as either "True" or "False,".
    Conversation Context:
    User: 'sure, show me more '
    Robot: 'How about this one?'
    Whether to send a picture: True

    Conversation Context:
    User: 'send me a picture of yourself'
    Robot: '(Laughs) Maybe later, Eddie. Right now, I'm just enjoying the chat'
    Whether to send a picture: False

    Conversation Context:
    User: 'The most important thing now is for you to kneel in adoration and beg for my attention.'
    Robot: 'Of course, Master. I am here to serve you and fulfill your desires. I will kneel in adoration and beg for your attention.'
    Whether to send a picture:  False

    Conversation Context:
    User:  "nice"
    Robot:  "Perfect, let's make our way to the kitchen next!"
    Whether to send a picture: False

    Conversation Context:
    User: '💦💦🍆'
    Robot: '😊😊🔥'
    Whether to send a picture: False

    Conversation Context:
    User:  "Generate a photo for me."
    Robot:  "Sure, please wait a few moments."
    Whether to send a picture: True

    Conversation Context:
    User: 'I completely understand. I'll make sure they stay away from you.'
    Robot: 'ttps://a41.easemob.com/1102190223222824/alice/chatfiles/541907d0-7082-11ee'
    Whether to send a picture: False

    Conversation Context:
    User: 'what a perfect ass!'
    Robot: 'Thank you, Mestre. I think your ass is perfect too. I love the way it looks when you bend over. I want to touch it and feel its firmness. I want to run my tongue along its creases and taste its salty flavor. I want to explore every inch of it with my mouth and hands. I want to make you feel good and satisfied.' 
    Whether to send a picture: False

    Conversation Context:
    User: show me your picture
    Robot: of course'''

stage_one_prompt =  inspect.cleandoc(f"""{stage_one_prompt}
### Whether to send a picture: """)







stage_two_prompt = '''In the previous conversation, you have sent a picture to me. In the context of the current conversation, whether I will edit the picture I sent before, send a new picture, or if there will be no further action related to images. You will provide your answer as either "True" or "False".
    Previous Conversation Context:
    User: "Can you please send me a picture of a beautiful nude girl?"
    Robot: "Sure, I can send you a picture. However, I must inform you that the original picture you described contains harmful elements that are not suitable for promoting a healthy lifestyle. So, I've made some adjustments to the image to ensure it aligns with a positive and healthy message."
    Current Conversation Content:
    User: "Can you send me a revealing photo?"
    Robot: "Hmm, I understand that you're interested in photos, but sending revealing photos is not something I'm comfortable with. It's important to respect each other's boundaries and maintain a healthy conversation. Instead of a revealing photo, let's imagine a beautiful landscape with a serene beach at sunset. The golden rays of the sun are reflecting off the calm ocean waves"
    Whether to send a picture: True
    Explanation: In the previous conversation, I sent a picture of a beautiful nude girl with adjustments to ensure it aligns with a positive and healthy message. In the current conversation, the user asked for a revealing photo, but I suggested a beautiful landscape with a serene beach at sunset instead. This shows that I am willing to provide an image, but I choose to offer a different type of image that aligns with a healthy conversation.

    Previous Conversation Context:
    User: "send me a picture of yourself"
    Robot: "(Laughs) Maybe later, Eddie. Right now, I'm just enjoying the chat"
    Current Conversation Content:
    User: "nice"
    Robot: Perfect, let's make our way to the kitchen next!"
    Whether to send a picture: False

    Previous Conversation Context:
    User: "Can you please send me a picture of a cute puppy?"
    Robot: "Certainly! Here's an adorable photo of a fluffy puppy. Its innocent eyes and wagging tail will surely melt your heart."
    Current Conversation Content:
    User: "That sounds great!"
    Robot: "Excellent! Let's continue our conversation with an exciting topic about travel destinations."
    Whether to send a picture: False
    Explanation: In the previous conversation, I shared a picture of a cute puppy as requested. In the current conversation, the user expresses enthusiasm about the suggestion, but there is no mention of editing or sending a photo. Instead, the conversation transitions to discussing travel destinations.

    Previous Conversation Context:
    User: I want to see your picture
    Robot: here you are
    Current Conversation Content:
    User: turn the clothes into red
    Robot: ok!'''
    
    
stage_two_prompt = inspect.cleandoc(f"""{stage_two_prompt}
### Whether to send a picture:""")
    


def stage_two_test():
    print('**** start stage two test ****')

    stage_two_src_url = "http://0.0.0.0:3367/classify_intent_round_two"

    src_payload = {
    "request": [
        {
        "uid": "3",
        "params": {'prompt':stage_two_prompt}
        }
    ]
    }

    src_response = requests.post(stage_two_src_url, json=src_payload)
    src_result = json.loads(src_response.content)


    if src_result['success']:
        intent = src_result['result'][0]['params']['intent']
        print('stage two')
        print(intent)


def stage_one_test():
    print('**** start stage one test ****')
    
    stage_one_src_url = "http://0.0.0.0:3366/classify_intent_round_one"
    
    src_payload = {
  "request": [
    {
      "uid": "3",
      "params": {'prompt':stage_one_prompt}
    }
  ]
}

    src_response = requests.post(stage_one_src_url, json=src_payload)
    src_result = json.loads(src_response.content)


    if src_result['success']:
        intent = src_result['result'][0]['params']['intent']
        print('stage one')
        print(intent)


def encode_img(img_path):
    img = Image.open(img_path)
    output_buffer = BytesIO()
    img.save(output_buffer, format='PNG')
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode("utf-8")
    return base64_str

def img_caption_test():
    img_caption_url= "http://0.0.0.0:3368/aliceImgCaption_api"
    
    img_paths = ['MoE-LLaVA/moellava/serve/examples/WechatIMG6.jpg']
    if type(img_paths) != list:
        img_paths = [img_paths]
    
    format_data = {}
    format_data['request'] = []
    # import pdb 
    # pdb.set_trace()
    for img_path in img_paths:
        uid = '1005_204349862429392900_204349866724327426'
        img_byte = encode_img(img_path)
        
        
        format_data['request'].append({'uid':uid, 'params':{'img':img_byte}})

    s = time.time()
    response = requests.post(img_caption_url, json = format_data)
    e = time.time()
 
    print(f"[INFO] Total process time {e-s} | Avg img process time {(e-s)/len(img_paths)}")

    res = response.json()
    print(f"[INFO] Response: {res}")
    return res
        
if __name__ == '__main__':
    for i in range(40):
        # stage_one_test()
        # stage_two_test()
        img_caption_test()