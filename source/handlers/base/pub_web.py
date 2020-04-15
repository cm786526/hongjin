import datetime

from sqlalchemy import or_
import tornado.escape

from handlers.base.webbase import BaseHandler
from dal.db_configs import DBSession,statistic_DBSession
import dal.models as models
from settings import ROOT_HOST_NAME,MP_APPID,APP_OAUTH_CALLBACK_URL
import re
# 全局基类方法
class GlobalBaseHandler(BaseHandler):
    # senguocc数据库会话
    @property
    def session(self):
        if hasattr(self, "_session"):
            return self._session
        self._session = DBSession()
        return self._session

    @property
    def statistic_session(self):
        if hasattr(self, "_statistic_session"):
            return self._statistic_session
        self._statistic_session = statistic_DBSession()
        return self._statistic_session

    # 关闭数据库会话
    def on_finish(self):
        if hasattr(self, "_session"):
            self._session.close()
        if hasattr(self, "_statistic_session"):
            self._statistic_session.close()

    # 判断是否为微信浏览器
    def is_wexin_browser(self):
        if "User-Agent" in self.request.headers:
            ua = self.request.headers["User-Agent"]
        else:
            ua = ""
        return "MicroMessenger" in ua

    # 判断是否为PC浏览器
    def is_pc_browser(self):
        if "User-Agent" in self.request.headers:
            ua = self.request.headers["User-Agent"]
        else:
            ua = ""
        return not ("Mobile" in ua)

    #判断是否是采购助手APP
    def is_carrefour_app(self):
        if "User-Agent" in self.request.headers:
            ua = self.request.headers["User-Agent"]
        else:
            ua = ""
        return "senguo:cfapp" in ua

    # 错误页面的处理
    def write_error(self, status_code, error_msg='', error_deal='', **kwargs):
        request_uri = self.request.uri
        method      = self.request.method.upper()
        if status_code == 400:
            if method == "POST":
                self.send_fail("参数错误: %s" % error_msg,400)
            else:
                self.render('notice/400.html', error_msg = error_msg, error_deal = error_deal, return_url ="/")
        elif status_code == 404:
            if method == "POST":
                self.send_fail("地址错误",404)
            else:
                self.render('notice/404.html', error_msg = error_msg, error_deal = error_deal, return_url ="/")
        elif status_code == 500:
            # from handlers.server_alarm import ServerAlarm
            # ServerAlarm.send_server_error(self.session,request_uri,**kwargs)
            if method == "POST":
                self.send_fail("系统错误",500)
            else:
                self.render('notice/500.html', error_msg = error_msg, error_deal = error_deal, return_url ="/")
        elif status_code == 403:
            if method == "POST":
                if not self.current_user:
                    return_url = self.reverse_url("Login")
                    self.send_fail("您的登录已过期，请重新登录",4031,return_url)
                else:
                    self.send_fail("没有权限",4032)
            else:
                self.render('notice/404.html', error_msg = error_msg, error_deal = error_deal, return_url ="/")
        else:
            super(GlobalBaseHandler, self).write_error(status_code, **kwargs)


# 登录、账户等基类方法
class _AccountBaseHandler(GlobalBaseHandler):
    _wx_oauth_weixin = "https://open.weixin.qq.com/connect/oauth2/authorize?appid={appid}&redirect_uri={redirect_uri}&response_type=code&scope=snsapi_userinfo&state=onfuckweixin#wechat_redirect"

    # overwrite this to specify which account is used
    __account_model__ = models.Accountinfo
    __account_cookie_name__ = "cguser_id"
    __token_cookie_name__ = "cg_token"
    __wexin_oauth_url_name__ = "oauth"


    # 获取当前用户（判断用户是否登录）
    def get_current_user(self):
        if not self.__account_model__ or not self.__account_cookie_name__:
            raise Exception("overwrite model to support authenticate.")
        if hasattr(self, "_user"):
            return self._user
        user_id = self.get_secure_cookie(self.__account_cookie_name__) or b'0'
        user_id = int(user_id.decode())

        token = self.__account_model__.get_pwd_token(self.session,user_id)
        if (not token) or (token == self.get_cookie(self.__token_cookie_name__)):
            token_checked = True
        else:
            token_checked = False

        if user_id and token_checked:
            self._user = self.__account_model__.get_by_id(self.session, user_id)
        else:
            self._user = None
        return self._user

    # 设置当前用户
    _ARG_DEFAULT = []
    def set_current_user(self, user, domain=_ARG_DEFAULT):
        if not self.__account_model__ or not self.__account_cookie_name__:
            raise Exception("overwrite model to support authenticate.")
        if domain is _AccountBaseHandler._ARG_DEFAULT:
            self.set_secure_cookie(self.__account_cookie_name__, str(user.id))
            self.set_cookie(self.__token_cookie_name__,self.__account_model__.get_pwd_token(self.session,user.id),expires_days=30)
        else:
            self.set_secure_cookie(self.__account_cookie_name__, str(user.id), domain=domain)
            self.set_cookie(self.__token_cookie_name__,self.__account_model__.get_pwd_token(self.session,user.id),domain=domain,expires_days=30)

    # 清除当前用户
    def clear_current_user(self):
        if not self.__account_model__ or not self.__account_cookie_name__:
            raise Exception("overwrite model to support authenticate.")
        self.clear_cookie(self.__account_cookie_name__, domain=ROOT_HOST_NAME)
        self.clear_cookie('cg_token', domain=ROOT_HOST_NAME)

    # 获取服务号微信授权登录链接
    def get_wexin_oauth_link(self, next_url=""):
        if not self.__wexin_oauth_url_name__:
            raise Exception("you have to complete this wexin oauth config.")
        if next_url:
            para_str = "?next="+tornado.escape.url_escape(next_url)
        else:
            para_str = ""
        # 微信中使用公众号授权
        if self.is_wexin_browser():
            if para_str:
                para_str += "&"
            else:
                para_str = "?"
            para_str += "mode=mp"
            redirect_uri = tornado.escape.url_escape(
                APP_OAUTH_CALLBACK_URL+\
                self.reverse_url(self.__wexin_oauth_url_name__) + para_str)
            link =  self._wx_oauth_weixin.format(appid=MP_APPID, redirect_uri=redirect_uri)
            return link

    def get_current_user_info(self):
        current_user = self.current_user
        user_info = {}
        if current_user:
            user_info["id"]=current_user.id
            user_info["nickname"] = current_user.nickname or current_user.realname
            user_info["imgurl"] = current_user.head_imgurl_small or ""
            user_info["sex"] = current_user.sex
            user_info["phone"] = current_user.phone or ""
        return user_info

#特殊字符
class Emoji():
    @classmethod
    def filter_emoji(cls,keyword):
        keyword=re.compile(u'[\U00010000-\U0010ffff]').sub(u'',keyword)
        return keyword

    @classmethod
    def check_emoji(cls,keyword):
        reg_emoji = re.compile(u'[\U00010000-\U0010ffff]')
        has_emoji = re.search(reg_emoji,keyword)
        if has_emoji:
            return True
        else:
            return False
# 录入员基类及方法
class RecordBaseHandler(_AccountBaseHandler):
    def get_user_role(self):
        return ""

    def get_login_url(self):
        return self.reverse_url('Login')

    @tornado.web.authenticated
    def prepare(self):
        """
            所有用户都必须要有手机号,没有手机号需重定向至手机号绑定页面
        """
        if not self.current_user.phone:
            return self.redirect(self.reverse_url("PhoneBind"))
# 录入员基类及方法
class AdminBaseHandler(_AccountBaseHandler):
    def get_user_role(self):
        return ""

    def get_login_url(self):
        return self.reverse_url('Login')

    @tornado.web.authenticated
    def prepare(self):
        """
            所有用户都必须要有手机号,没有手机号需重定向至手机号绑定页面
        """
        if not self.current_user.phone:
            return self.redirect(self.reverse_url("PhoneBind"))
