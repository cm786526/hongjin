
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from sqlalchemy.sql import func
import dal.models as models
from handlers.base.pub_web import _AccountBaseHandler,Emoji
from handlers.base.pub_wx_web import WxOauth2,WxTicketUrl
from handlers.base.pub_func import Emoji
from libs.msgverify import check_msg_token
from settings import ROOT_HOST_NAME
from libs.senguo_encrypt import SimpleEncrypt
class Login(_AccountBaseHandler):
    """登录
    """
    def initialize(self,action):
        self._action = action

    @_AccountBaseHandler.check_arguments("next?:str")
    def get(self):
        next_url = self.get_argument("next", "")
        if self._action == "login":
            if self.current_user:
                Accountinfo=models.Accountinfo
                account_info = self.session.query(Accountinfo).filter_by(id = self.current_user.id).first()
                self.which_staff_belong("get",account_info)
            else:
                return self.render("login/login.html")
        # 管理员后台退出登录
        elif self._action == "logout":
            self.clear_current_user()
            redirect_url = self.reverse_url("Login")
            if next_url:
                if next_url == "super":
                    redirect_url = self.reverse_url("superLogin")
                else:
                    redirect_url += "?next=%s"%next_url
            return self.redirect(redirect_url)
        # 处理微信的授权登录跳转
        elif self._action == "oauth":
            return self.handle_oauth(next_url)
        elif self._action == "weixin":
            return self.redirect(self.get_wexin_oauth_link(next_url))
        else:
            return self.send_error(404)
    @_AccountBaseHandler.check_arguments("code:str", "state?:str", "mode:str")
    def handle_oauth(self,next_url):
        """app微信授权登录
        """
        code = self.args["code"]
        mode = self.args["mode"]
        if mode not in ["mp", "carrefour"]:
            return self.send_error(400)
        userinfo = WxOauth2.get_userinfo(code, mode)
        if not userinfo:
            return self.redirect(self.reverse_url("Login"))
        session = self.session
        Accountinfo=models.Accountinfo

        u = models.Accountinfo.register_with_wx(session, userinfo)
        self.set_current_user(u, domain=ROOT_HOST_NAME)
        current_user = u
        user_info = {}
        if current_user:
            if current_user.phone:
                # 如果已经绑定了手机　直接跳过
                return self.which_staff_belong("get",current_user)
            user_info["id"]=current_user.id
            user_info["nickname"] = current_user.nickname or current_user.realname
            user_info["imgurl"] = current_user.head_imgurl_small or ""
            user_info["sex"] = current_user.sex
            user_info["phone"] = current_user.phone or ""
        return self.render("login/bind.html",user_info=user_info)

    @_AccountBaseHandler.check_arguments("action:str")
    def post(self):
        action = self.args["action"]
        if action == "phone_password":
            return self.login_by_phone_password()
        elif action == "phone_code":
            return self.login_by_phone_code()
        elif action == "wx_ticket":
            return self.login_by_wx_ticket()
        elif action == "get_wx_ticket":
            return self.get_wx_ticket()
        elif action == "login_bind_phone":
            return self.login_bind_phone()
        elif action == "phone_regist":
            return self.phone_regist()
        else:
            return self.send_fail(404)

    @_AccountBaseHandler.check_arguments("phone:str","password:str")
    def login_by_phone_password(self):
        """手机号+密码登录
            phone:手机号
            password:密码
        """
        session = self.session
        phone = self.args["phone"]
        password = self.args["password"]
        password=SimpleEncrypt.encrypt(password)
        u = models.Accountinfo.login_by_phone_password(session, phone, password)
        if not u:
            return self.send_fail("用户名或密码错误")
        self.set_current_user(u, domain=ROOT_HOST_NAME)
        self.which_staff_belong("post",u)

    @_AccountBaseHandler.check_arguments("phone:str","code:str")
    def login_by_phone_code(self):
        """手机号+验证码登录，已注册用户直接登录，未注册用户生成新账号并登录
            phone:手机号
            code:验证码
        """
        phone = self.args["phone"]
        code = self.args["code"]
        session = self.session
        Accountinfo = models.Accountinfo

        # 用于app审核
        if phone == "18299999999" and code == "9823":
            phone = "13125182048"
        else:
            check_msg_res = check_msg_token(phone, code, use="login")
            if not check_msg_res:
                return self.send_fail("验证码过期或者不正确")

        try:
            account = session.query(Accountinfo).filter_by(phone = phone).one()
        except NoResultFound:
            account = None

        if not account:
            account = Accountinfo.register_with_phone(session,phone)
            #每当有一个新用户注册的时候，就要对应的增加录入设置的信息
            Accountinfo.init_recorder_settings(session,account.id)
            temp_name = Accountinfo.create_temp_name()
            temp_name = "用户{}".format(temp_name)
            account.nickname = temp_name
            account.realname = temp_name

        session.commit()

        bind_wx = True if account.wx_unionid else False
        self.set_current_user(account, domain=ROOT_HOST_NAME)
        self.which_staff_belong("post",account)

    @_AccountBaseHandler.check_arguments("scene_id:int")
    def login_by_wx_ticket(self):
        """微信二维码登录
            scene_id:二维码场景值
        """
        scene_id = self.args['scene_id']
        openid = redis.get('cg_scene_openid:%s' % scene_id)           #检查用户是否扫码
        bind_fail = redis.get('cg_scene_openid_fail:%s' % scene_id)   #该项有值则证明用户微信绑定失败
        bind_phone = False
        bind_wx = False
        session = self.session
        if openid:
            #这个判断用于判断用户扫码状态是处于微信绑定场景
            if bind_fail:
                return self.send_fail("该微信已和其他手机号绑定，请更换微信或联系森果客服 4000270135")
            #下面的场景应用于登录或微信绑定成功后的跳转
            openid = openid.decode('utf-8')
            u = session.query(models.Accountinfo).filter_by(wx_openid = openid).first()
            if u:
                self.set_current_user(u,domain=ROOT_HOST_NAME)
                redis.delete('cg_scene_openid:%s' % scene_id)
                if u.phone:
                    bind_phone = True
            bind_wx = True
            return self.send_success(login=True,bind_phone=bind_phone,bind_wx=bind_wx)
        else:
            return self.send_success(login=False,bind_phone=bind_phone,bind_wx=bind_wx)


    @_AccountBaseHandler.check_arguments("phone:str","code:str","name:str")
    def login_bind_phone(self):
        """微信登录后进行手机绑定
            phone:手机号
            code:验证码
            name:真实姓名
        """
        filter_emoji = Emoji.filter_emoji
        code = self.args["code"]
        phone = filter_emoji(self.args["phone"].strip())
        name = filter_emoji(self.args.get("name","").strip())
        current_user = self.current_user
        Accountinfo=models.Accountinfo
        if not current_user:
            return self.send_fail("请先使用微信登录")
        session = self.session
        if current_user.phone:
            return self.send_fail("您已绑定手机号，请前往个人中心进行修改")
        if current_user.phone == phone:
            return self.send_fail("您已绑定该手机号")
        if not current_user.wx_unionid:
            return self.send_fail("请使用微信登录")
        check_msg_res = check_msg_token(phone, code, use="bind")
        if not check_msg_res:
            return self.send_fail("验证码过期或者不正确")
        exist_account = session.query(Accountinfo).filter_by(phone = phone).first()
        if exist_account:
            if exist_account.wx_unionid:
                return self.send_fail("该手机号已绑定其他微信")
            origin_wx_unionid = current_user.wx_unionid
            origin_wx_openid = current_user.wx_openid
            origin_wx_country = current_user.wx_country
            origin_wx_province = current_user.wx_province
            origin_wx_city = current_user.wx_city
            origin_nickname = current_user.nickname
            origin_headimgurl = current_user.headimgurl
            origin_sex  = current_user.sex
            #清空微信所在账户信息
            current_user.wx_unionid = None
            current_user.wx_openid = None
            session.flush()

            #将微信信息绑定到已有的手机账户上并跳转到已有账户
            exist_account.wx_unionid = origin_wx_unionid
            exist_account.wx_openid = origin_wx_openid
            exist_account.wx_country = origin_wx_country
            exist_account.wx_province = origin_wx_province
            exist_account.wx_city = origin_wx_city
            exist_account.nickname = origin_nickname
            exist_account.realname = name
            exist_account.headimgurl = origin_headimgurl
            exist_account.sex=origin_sex
            session.delete(current_user)
            session.commit()
            self.set_current_user(exist_account,domain=ROOT_HOST_NAME)
            self.which_staff_belong("post",exist_account)
        else:
            current_user.phone = phone
            current_user.realname = name
            #每当有一个新用户注册的时候，就要对应的增加录入设置的信息
            Accountinfo.init_recorder_settings(session,current_user.id)
            session.commit()
            self.which_staff_belong("post",current_user)
    def get_wx_ticket(self):
        ticket_url , scene_id = WxTicketUrl.get_ticket_url()
        return self.send_success(ticket_url=ticket_url,scene_id=scene_id)
    # 使用手机号注册账户
    @_AccountBaseHandler.check_arguments("phone:str","code:str","name:str")
    def phone_regist(self):
        filter_emoji = Emoji.filter_emoji
        code = self.args["code"]
        phone = filter_emoji(self.args["phone"].strip())
        name = filter_emoji(self.args.get("name","").strip())
        session = self.session
        exist_account = session.query(models.Accountinfo).filter_by(phone = phone).first()
        if exist_account:
            return self.send_fail("您已注册，如果您已是员工，请直接登录；如还不是员工请先使用手机号添加成为员工")

        check_msg_res = check_msg_token(phone, code, use="register")
        if not check_msg_res:
            return self.send_fail("验证码过期或者不正确")

        Accountinfo=models.Accountinfo
        account_info = Accountinfo(
                phone  = phone,
                nickname=name,
                realname=name
            )

        session.add(account_info)
        session.flush()
        self.set_current_user(account_info,domain=ROOT_HOST_NAME)
        #每当有一个新用户注册的时候，就要对应的增加录入设置的信息
        Accountinfo.init_recorder_settings(session,account_info.id)
        session.commit()
        return self.send_success()
    # 判断是属于哪种类型用户,并且进行相应的跳转
    def which_staff_belong(self,request_type,account_info):
        # 判断当前用户有没有被添加为员工
        current_user_id=account_info.id
        session=self.session
        HireLink=models.HireLink
        max_staff=session.query(func.max(HireLink.active_admin),\
                                func.max(HireLink.active_recorder))\
                        .filter_by(staff_id=current_user_id)\
                        .first()
        #获取个人信息
        account_info_dict={
            "id":account_info.id,
            "headimgurl":account_info.headimgurl,
            "phone":account_info.phone,
            "nickname":account_info.nickname
        }
        # 如果是get请求　则可以后台跳转
        if request_type=="get":
            if max_staff:
                # 管理员
                if max_staff[0]==1:
                    return self.redirect(self.reverse_url("shopmanage"))
                # 录入员
                elif max_staff[1]==1:
                    return self.redirect(self.reverse_url("recordergoodsmanage"))
                else:
                # 都不是则直接跳转到提示页面
                    return self.render("login/login-tip.html",account_info_dict=account_info_dict)
            # 直接跳转到提示页面
            else:
                return self.render("login/login-tip.html",account_info_dict=account_info_dict)
        # post请求则只能前端进行跳转
        else:
            next_url=""
            if max_staff:
                if max_staff[0]==1:
                    # 管理员
                    next_url=self.reverse_url("shopmanage")
                elif max_staff[1]==1:
                    # 录入员
                    next_url=self.reverse_url("recordergoodsmanage")
                else:
                    next_url=self.reverse_url("Login")
            # 对于post请求需要前端做跳转
            return self.send_success(next_url=next_url)


class PhoneBind(_AccountBaseHandler):
    """app端微信登录后绑定手机号
    """
    @_AccountBaseHandler.check_arguments("next?:str")
    def get(self):
        if not self.current_user:
            return self.redirect(self.reverse_url("Login"))
        if self.current_user.phone:
            pass
            # return self.redirect(self.reverse_url("shopmanage"))
        user_info = self.get_current_user_info()
        return self.render("login/bind.html",user_info=user_info)
