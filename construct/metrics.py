import functools
import socket
import subprocess
import logging
import time
import random
import json
import threading
import traceback

logger = logging.getLogger(__name__)
metrics_buffer = []
BUFFER_THRESHOLD = 3
MAX_WAITE_SECOND = 1
last_send_time = 0


def _connect():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("172.31.129.234", 18888))
        s.settimeout(0.0)
        return s
    except Exception as e:
        logger.error('metrics connect: {}'.format(str(e)))
        return False


_s = _connect()


def _do_send():
    global metrics_buffer, _s
    if not _s:
        _s = _connect()
    metrics_buffer, pre_buffer = [], metrics_buffer
    if len(pre_buffer) == 0:
        return True
    try:
        to_send = "{:04x}{}".format(len(pre_buffer),
                                    '\n'.join(['{}\t{}\t{}'.format(m[0], m[1], _json_dumps(m[2])) for m in pre_buffer]))
        to_send_bytes = bytes(to_send, encoding='utf-8')
        res = _s.sendall(to_send_bytes)
        return True
    except Exception as e:
        metrics_buffer.extend(pre_buffer)
        _s = _connect()
        logger.error("metrics failed to send:{},reason:{}".format(pre_buffer, traceback.format_exc()))
    return False


def _send(name, value, ext=None, oneshot=False, test_dup=0):
    global metrics_buffer
    metrics_buffer.append((name, value, ext))
    test_dup += 1
    if len(metrics_buffer) >= BUFFER_THRESHOLD or oneshot:
        for _ in range(test_dup):
            if _do_send():
                return True
    else:
        return True
    return False


def _json_dumps(ext):
    if not ext or not isinstance(ext, dict):
        return ''
    res = []
    for k in sorted(ext.keys()):
        v = ext[k]
        try:
            if len(v) == 24 and int(v, 16):
                continue
        except Exception:
            pass
        res.append(json.dumps(k) + ":" + json.dumps(v))
    return '{' + ','.join(res) + "}"


def emit_metrics(name, value: float = 1, ext=None, drop=0.0, test_dup=0, oneshot=False):
    if drop and random.random() < drop:
        return True
    _send(name, value, ext, oneshot, test_dup)


def emit_metrics_grace_full(name, value: float = 1, ext=None, drop=0.0, test_dup=0, oneshot=False):
    try:
        emit_metrics(name, value=value, ext=ext, drop=drop, test_dup=test_dup, oneshot=oneshot)
    except Exception as e:
        logger.error("emit_metric_error:{}".format(name))


def emit_metrics_latency_survey(name, diff):
    if diff < 1:
        emit_metrics(name + (".lat.s%.1f" % diff), 1)
    elif diff < 10:
        emit_metrics(name + ".lat.s" + str(int(diff)), 1)
    else:
        emit_metrics(name + ".lat.s10", 1)


def timing_metrics(prefix='', respect_exception=False):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            name = ('' if not prefix else prefix + '.') + f.func_name + ".avg"
            start = time.time()
            if respect_exception:
                res = f(*args, **kwargs)
                emit_metrics(name, time.time() - start)
                return res
            else:
                try:
                    return f(*args, **kwargs)
                finally:
                    emit_metrics(name, time.time() - start)

        return wrapper

    return decorator


def timing_datasource(tag):
    import inspect

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return f(*args, **kwargs)
            finally:
                if f.func_name == "c_online_limit":
                    if random.randint(0, 1000) == 0:
                        try:
                            caller = inspect.stack()[1][3]
                            emit_metrics("mongo." + tag + "." + f.func_name + ".k." + str(caller), 1)
                        except Exception:
                            pass
                emit_metrics("mongo." + tag + "." + f.func_name + ".avg", time.time() - start)

        return wrapper

    return decorator


def init_metrics():
    try:
        r = subprocess.getoutput('git log -n1 --format=format:"%H [%cd] %cn %s"').strip()
        h = r[:40]
        if 'Merge branch' in r:
            r = subprocess.getoutput('git log -n1 --format=format:"%H [%cd] %cn %s" HEAD^2').strip()
            emit_metrics("_gometrics_report_githash", 1, {'hash': h, 'msg': '<M>' + r[41:]})
        else:
            emit_metrics("_gometrics_report_githash", 1, {'hash': h, 'msg': r[41:]})
    except Exception as e:
        logger.error(str(e))


_timed_thread: threading.Thread


def thread_work():
    while True:
        time.sleep(MAX_WAITE_SECOND)
        try:
            _do_send()
        except Exception:
            logger.warning("sending exception:{}".format(traceback.format_exc()))


def init_timed_thread():
    global _timed_thread
    if _timed_thread is not None:
        return
    _timed_thread = threading.Thread(target=thread_work)
    _timed_thread.setName("timed metric thread")
    _timed_thread.setDaemon(True)
    _timed_thread.start()
