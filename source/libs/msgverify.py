import random
from tornado.options import options
from dal.db_configs import redis
from dal.models import VerifyCodeUse
from libs.yunpian import send_yunpian_verify_code

##################################################################################
# 短信平台 自带验证过程，因此去掉本地的检测过程，避免因不必要的错误导致用户发不出去
##################################################################################

def gen_msg_token(phone, use):
    """生成并发送验证码，将验证码存储到redis中，缓存5分钟。

    输入参数：
    phone 发送对象的手机号
    use 验证码用途标志，会存储在redis中，同时通过此标志获取用途文本并展示在短信中

    返回值：
    发送成功时返回True，否则返回False或错误提示
    """
    population_seq = "0123456789"   # 组成验证码元素的序列
    code_length = 4                 # 验证码长度
    expire_minutes = 5              # 验证码有效时间

    # 获取验证码用途文本
    use_text = VerifyCodeUse.get_use_text(use)
    if not use_text:
        return "invalid use type"
    # 生成验证码
    code = "".join([random.choice(population_seq) for i in range(code_length)])
    # 发送验证码
    if options.debug:
        print("VerifyCode:",code)
        status = True
    else:
        status = send_yunpian_verify_code(phone, code, use_text)
    # 存储验证码
    if status is True:
        h = "cf_verify_code:{}:{}".format(use, phone)
        redis.set(h, code, expire_minutes*60)
        return True
    else:
        return status

# 检查验证码
def check_msg_token(phone, code, use):
    h = "cf_verify_code:{}:{}".format(use, phone)
    old_code = redis.get(h)
    redis.delete(h)
    if old_code and old_code.decode("utf-8") == str(code):
        return True
    else:
        return False