import requests
from io import BytesIO
from PIL import Image
import logging
import base64
from textblob import Word
import re
import os 
import pandas as pd
import base64


def initialize_logger():
    # 配置日志记录器
    logger = logging.getLogger('my_logger')  # 创建一个日志记录器
    logger.setLevel(logging.INFO)  # 设置日志记录级别为INFO
 
    console_handler = logging.StreamHandler()  # 创建一个控制台处理器，指定日志输出到控制台

    # 配置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # 设置日志格式

    # 将日志格式应用到处理器
    console_handler.setFormatter(formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(console_handler)

    return logger


def base642Pil(base64_data):
    byte_data = base64.b64decode(base64_data)
    image_data = BytesIO(byte_data)
    img = Image.open(image_data)
    if img.mode != "RGB":
        img = img.convert(mode="RGB")
    return img