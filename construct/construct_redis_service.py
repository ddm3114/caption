# coding: utf-8
import time
import os
import redis


class ConstructRedis:
    redis_obj = None

    CLEAR_SCRIPT = """
    local field = ARGV[1]
    local origin = redis.call("hget", KEYS[1], field)
    if not origin then
        return true
    end
    if origin == ARGV[2] then
        redis.call("hdel", KEYS[1], field)
        redis.call("hdel", KEYS[2], field)
    end
    return true
    """
    CLEAR_CMD = None


    @classmethod
    def init_redis_db(cls, dev=False):
        region = os.getenv('DC_REGION')

        if region and region == "us-east-1":
            # USA EAST
            if dev is True:
                # Test
                HOST = "r-0xigo5c8tcfatuhfue.redis.rds.aliyuncs.com"
                PASS = "xrUmFIPy9r86Q"
            else:
                # Online
                HOST = "r-0xiukxvcpxl49asf32.redis.rds.aliyuncs.com"
                PASS = "xrUmFIPy9r86Q^9"
        else:
            # SINGAPROE
            if dev is True:
                # Test
                HOST = "r-j6ck9g0jbbdils1ug7.redis.rds.aliyuncs.com"
                PASS = "s-%S&mGh8jow"
            else:
                #Online 
                HOST = "r-j6c5c5o0l7zzduz1tx.redis.rds.aliyuncs.com"
                PASS = "hFj$5#sgf76#k#&j3"

        if not cls.redis_obj:
            cls.redis_obj = redis.StrictRedis(
                host=HOST,
                password=PASS,
                port=6379,
                db=0
            )
            cls.CLEAR_CMD = cls.redis_obj.register_script(cls.CLEAR_SCRIPT)
        return

    @classmethod
    def get_redis_obj(cls):
        return cls.redis_obj

    @classmethod
    def clear(cls, timeout=300, key="aigc_fast_chat", dev=False):
        cls.init_redis_db(dev=dev)
        now = int(time.time())
        ealier = now-timeout
        key_heartbeat = "{"+key+"}_heart_beat"
        key_info = "{"+key+"}_info"
        redis_obj: redis.StrictRedis = cls.get_redis_obj()
        item_dict:dict = redis_obj.hgetall(key_heartbeat)
        for k, v in item_dict.items():
            to_remove = True
            try:
                v_int = int(v)
                if v_int >= ealier:
                    to_remove = False
            except Exception:
                pass
            if to_remove:
                cls.CLEAR_CMD(keys=[key_heartbeat, key_info], args=[k, v])


if __name__ == "__main__":
    ConstructRedis.clear(timeout=300)