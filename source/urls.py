# 头部引入handlers中的模块
import handlers.login
import handlers.common

# urls.py
handlers = [
    # 登录
    (r"/login", handlers.login.Login, {"action":"login"}, "Login"),
    (r"/logout", handlers.login.Login, {"action":"logout"}, "Logout"),
    (r"/login/oauth", handlers.login.Login, {"action":"oauth"}, "oauth"),
    (r"/login/phonebind", handlers.login.PhoneBind, {}, "PhoneBind"),
    (r"/common/logincode", handlers.common.LoginVerifyCode, {}, 'commonLoginVerifyCode'),
    (r"/common/profile", handlers.common.Profile, {}, 'commonProfile'),
]
