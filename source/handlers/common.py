import tornado.web
from sqlalchemy import or_, func,and_
import datetime
from dal.db_configs import redis
from handlers.base.pub_web import _AccountBaseHandler,GlobalBaseHandler
from handlers.base.pub_func import TimeFunc,NumFunc
from libs.msgverify import gen_msg_token,check_msg_token
import dal.models as models
from libs.senguo_encrypt import SimpleEncrypt
from tornado.websocket import WebSocketHandler
import urllib
import logging


class LoginVerifyCode(_AccountBaseHandler):
    """未登录用户获取短信验证码，用于注册或登录"""
    def prepare(self):
        """屏蔽登录保护"""
        pass

    @_AccountBaseHandler.check_arguments("action:str", "phone:str")
    def post(self):
        action = self.args["action"]
        phone = self.args["phone"]
        if len(phone) != 11:
            return self.send_fail("请填写正确的手机号")
        if action not in models.VerifyCodeUse.login_verify_code_use:
            if action not in models.VerifyCodeUse.operation_verify_code_use:
                return self.send_fail("invalid action")
        # 发送验证码
        result = gen_msg_token(phone, action)
        if result is True:
            return self.send_success()
        else:
            return self.send_fail(result)


class Profile(_AccountBaseHandler):
    """个人中心
    """
    @tornado.web.authenticated
    def prepare(self):
        """
            所有用户都必须要有手机号,没有手机号需重定向至手机号绑定页面
        """
        if not self.current_user.phone:
            return self.redirect(self.reverse_url("PhoneBind"))

    def get(self):
        #获取个人信息
        return self.render("login/login.html")

    @_AccountBaseHandler.check_arguments("action:str")
    def post(self):
        action=self.args["action"]
        if action=="get_profile":
            return self.get_profile()
        elif action=="set_password":
            return self.set_password()
        elif action=="modify_password":
            return self.set_password()
        elif action=="modify_phone":
            return self.modify_phone()
        elif action=="change_role":
            return self.change_role()
        else:
            return self.send_fail(404)

    def get_profile(self):
        """ 获取个人信息
        """
        session=self.session
        current_user_id=self.current_user.id
        AccountInfo=models.Accountinfo
        account_info=session.query(AccountInfo)\
                            .filter_by(id=current_user_id)\
                            .first()
        account_dict={
            "id":account_info.id,
            "staff_id":account_info.id,
            "phone":account_info.phone,
            "realname":account_info.nickname,
            "headimgurl":account_info.headimgurl,
            "sex_text":account_info.sex_text
        }
        return self.send_success(account_dict=account_dict)

    @_AccountBaseHandler.check_arguments("password:str")
    def set_password(self):
        """ 设置密码
        """
        password=self.args["password"]
        password=SimpleEncrypt.encrypt(password)
        session=self.session
        current_user_id=self.current_user.id
        AccountInfo=models.Accountinfo
        account_info=session.query(AccountInfo)\
                            .filter_by(id=current_user_id)\
                            .first()
        account_info.password=password
        session.commit()
        return self.send_success()

    @_AccountBaseHandler.check_arguments("phone:str","code:str")
    def modify_phone(self):
        """ 修改手机号
        """
        phone=self.args["phone"]
        code=self.args["code"]
        session=self.session
        current_user_id=self.current_user.id
        AccountInfo=models.Accountinfo
        check_msg_res = check_msg_token(phone, code, use="bind")
        if not check_msg_res:
            return self.send_fail("验证码过期或者不正确")
        account_info=session.query(AccountInfo)\
                            .filter_by(id=current_user_id)\
                            .first()
        account_info.phone=phone
        session.commit()
        return self.send_success()

    @_AccountBaseHandler.check_arguments("target:str")
    def change_role(self):
        """切换角色
        """
        target=self.args["target"]
        # 判断用户是否可以切换
        current_user_id=self.current_user.id
        session=self.session
        HireLink=models.HireLink
        max_staff=session.query(func.max(HireLink.active_admin),\
                                func.max(HireLink.active_recorder))\
                        .filter_by(staff_id=current_user_id)\
                        .first()
        if target=="admin":
            if max_staff[0]:
                return self.send_success(next_url=self.reverse_url("shopmanage"))
            else:
                return self.send_fail("您不是管理员，不能切换到管理端")
        elif target=="recorder":
            if max_staff[1]:
                return self.send_success(next_url=self.reverse_url("recordergoodsmanage"))
            else:
                return self.send_fail("您不是录入员，不能切换到录入端")
        else:
            return self.send_fail(404)

class UpdateWebSocket(WebSocketHandler,_AccountBaseHandler):
    """websocket代替轮询获取更新的数据
    """
    # 保存连接的管理员，用于后续推送消息
    all_shop_admins = {}
    all_shop_recorders= {}
    def open(self):
        # print("new　client opened")
        # 根据cookie判断用户当前在管理端还是录入端
        user_type = self.get_cookie('user_type')
        HireLink=models.HireLink
        current_user_id=self.current_user.id
        all_shop_admins=UpdateWebSocket.all_shop_admins
        all_shop_recorders=UpdateWebSocket.all_shop_recorders
        session=self.session
        if user_type=="admin":
            # 判断连接的管理员所在店铺id
            all_shops=session.query(HireLink.shop_id)\
                                .filter_by(staff_id=current_user_id,\
                                            active_admin=1)\
                                .all()
            for each_shop in all_shops:
                _id=str(each_shop[0])
                if _id in all_shop_admins:
                    all_shop_admins[_id].append(self)
                else:
                    all_shop_admins[_id]=[self]
        elif user_type=="recorder":
            # 判断连接的录入员所在的店铺id
            all_shops=session.query(HireLink.shop_id)\
                                .filter_by(staff_id=current_user_id,\
                                            active_recorder=1)\
                                .all()
            for each_shop in all_shops:
                _id=str(each_shop[0])
                if _id in all_shop_recorders:
                    all_shop_recorders[_id].append(self)
                else:
                    all_shop_recorders[_id]=[self]

    def on_close(self):
        # print("one client closed")
        for value in UpdateWebSocket.all_shop_admins.values():
            if self in value:
                value.remove(self)

    # 录入员录入完成之后发送消息告诉管理员
    @classmethod
    def send_demand_updates(cls,message):
        logging.info("sending message to %d admins", len(cls.all_shop_admins))
        all_admins=[]
        shop_id=str(message["shop_id"])
        if shop_id in UpdateWebSocket.all_shop_admins:
            all_admins=UpdateWebSocket.all_shop_admins[shop_id]
        for _admin in all_admins:
            try:
                _admin.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)

    # 管理员修改预订系数之后告诉录入员
    @classmethod
    def send_ratio_updates(cls,message):
        logging.info("sending message to %d recorders", len(cls.all_shop_recorders))
        all_recorders=[]
        shop_id=str(message["shop_id"])
        if shop_id in UpdateWebSocket.all_shop_recorders:
            all_recorders=UpdateWebSocket.all_shop_recorders[shop_id]
        for _recorder in all_recorders:
            try:
                _recorder.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self,message):
        # 接收客户端发来的消息
        logging.info("got message %r", message)

    def check_origin(self, origin):
        parsed_origin = urllib.parse.urlparse(origin)
        return parsed_origin.netloc.index(".senguo.cc")!=-1

