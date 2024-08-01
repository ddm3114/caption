# coding: utf-8
import math
import socket


def get_my_ip():
    """
    returns ip / hostname of current host
    """
    # socket.gethostbyname(socket.gethostname()) gives a wrong result due to copy of image
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        st.connect(('10.255.255.255', 1))
        ip = st.getsockname()[0]
        return ip
    finally:
        st.close()


def get_outter_addr():
    return "0.0.0.0:9003"


def limit_latest(source: list, limit_num: int):
    if len(source) <= limit_num:
        return source
    return source[-limit_num:]


def handle_inf_to_list(source, default=999):
    if not source:
        return source
    return [handle_inf(item, default=default) for item in source]


def handle_inf(item, default=999):
    try:
        if not math.isinf(item):
            return item
        if item > 0:
            return default
        return -default
    except Exception:
        return item
