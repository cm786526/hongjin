import json
import urllib
import requests

from dal.db_configs import redis
from handlers.base.pub_web import _AccountBaseHandler
from settings import *


# 所有需要微信授权调用的东西，模版消息等
class WxOauth2(object):
    token_url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid={appid}" \
                "&secret={appsecret}&code={code}&grant_type=authorization_code"
    userinfo_url = "https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={openid}&lang=zh_CN"
    client_access_token_url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential" \
                              "&appid={appid}&secret={appsecret}".format(appid=MP_APPID, appsecret=MP_APPSECRET)
    jsapi_ticket_url = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi"
    template_msg_url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    # 获取用户微信资料（需用户授权）
    @classmethod
    def get_userinfo(cls, code, mode):
        data = cls.get_access_token_openid(code, mode)
        if not data:
            return None
        access_token, openid = data
        userinfo_url = cls.userinfo_url.format(access_token=access_token, openid=openid)
        try:
            data = json.loads(urllib.request.urlopen(userinfo_url).read().decode("utf-8"))
        except Exception as e:
            print(e)
            return None
        if "errcode" in data:
            return None
        return data

    # 获取用户微信 UnionID 和 OpenID（静默授权）
    @classmethod
    def get_userinfo_base(cls,code,mode):
        data = cls.get_access_token_openid(code,mode)
        if not data:
            return None
        access_token,openid = data
        access_token = cls.get_client_access_token()
        userinfo_url = 'https://api.weixin.qq.com/cgi-bin/user/info?access_token={0}&openid={1}'.format(access_token,openid)
        try:
            data = json.loads(urllib.request.urlopen(userinfo_url).read().decode('utf-8'))
            userinfo_data = dict(
                openid  = data['openid'],
                unionid = data['unionid']
            )
        except Exception as e:
            print(e)
            return None
        return userinfo_data

    # 获取用户微信 OpenID
    # access_token接口调用有次数上限，最好全局变量缓存
    # 这是需要用户授权才能获取的access_token
    @classmethod
    def get_access_token_openid(cls, code, mode):
        # 需要改成异步请求
        if mode == "kf":      # 从PC来的登录请求
            token_url = cls.token_url.format(
                code=code, appid=KF_APPID, appsecret=KF_APPSECRET)
        elif mode == "carrefour": # 从家乐福App来的登录请求
            token_url = cls.token_url.format(
                code=code, appid=CARREFOUR_APPID, appsecret=CARREFOUR_APPSECRET)
        else:
            token_url = cls.token_url.format(
                code=code, appid=MP_APPID, appsecret=MP_APPSECRET)
        # 获取access_token
        try:
            data = json.loads(urllib.request.urlopen(token_url).read().decode("utf-8"))
        except Exception as e:
            print("[WxOauth2]get_access_token_openid: Oauth2 Error, get access token failed")
            return None
        if "access_token" not in data:
            return None
        return (data["access_token"], data["openid"])

    # 获取用户微信 UnionID
    # access_token接口调用有次数上限，最好全局变量缓存
    # 这是需要用户授权才能获取的access_token
    @classmethod
    def get_access_token_unionid(cls, code, mode):
        # 需要改成异步请求
        if mode == "kf": # 从PC来的登录请求
            token_url = cls.token_url.format(
                code=code, appid=KF_APPID, appsecret=KF_APPSECRET)
        elif mode == "iOS": # 从iOS商家版App来的登录请求
            token_url = cls.token_url.format(
                code=code, appid=iOS_APPID, appsecret=iOS_APPSECRET)
        elif mode == "adroid": # 从iOS销售管理App来的登录请求
            token_url = cls.token_url.format(
                code=code, appid=Android_APPID, appsecret=Android_APPSECRET)
        else:
            token_url = cls.token_url.format(
                code=code, appid=MP_APPID, appsecret=MP_APPSECRET)
        # 获取access_token
        try:
            data = json.loads(urllib.request.urlopen(token_url).read().decode("utf-8"))
        except Exception as e:
            print("[WxOauth2]get_access_token_unionid: Oauth2 Error, get access token failed")
            return None
        if "access_token" not in data:
            return None
        return (data["access_token"], data["openid"], data["unionid"])

    # 获取微信模版消息模版的ID
    @classmethod
    def get_template_id(cls,admin_id,template_id_short,access_token):
        session = models.DBSession()
        admin = session.query(models.ShopAdmin).filter_by(id = admin_id).first()
        if not admin:
            session.close()
            return False
        template_id_zip = eval(admin.template_id)
        template_id = template_id_zip.get(template_id_short,None)
        if not template_id:
            url = 'https://api.weixin.qq.com/cgi-bin/template/api_add_template?access_token={0}'.format(access_token)
            data = json.dumps({"template_id_short":template_id_short})
            r = requests.post(url,data=data)
            s = r.text
            if isinstance(s,bytes):
                s = s.decode('utf-8')
            s = json.loads(s)
            template_id = s.get('template_id',None)
            if template_id is None:
                session.close()
                return False
            template_id_zip[template_id_short] = template_id
            admin.template_id = str(template_id_zip)
            session.commit()
        session.close()
        return template_id

    # 获取森果微信 jsapi ticket
    @classmethod
    def get_jsapi_ticket(cls):
        if datetime.datetime.now().timestamp() - jsapi_ticket["create_timestamp"]\
                < 7100 and jsapi_ticket["jsapi_ticket"]:  # jsapi_ticket过期时间为7200s，但为了保险起见7100s刷新一次
            return jsapi_ticket["jsapi_ticket"]
        access_token = cls.get_client_access_token()
        if not access_token:
            return None
        jsapi_ticket_url = cls.jsapi_ticket_url.format(access_token=access_token)

        data = json.loads(urllib.request.urlopen(jsapi_ticket_url).read().decode("utf-8"))
        if data["errcode"] == 0:
            jsapi_ticket["jsapi_ticket"] = data["ticket"]
            jsapi_ticket["create_timestamp"] = datetime.datetime.now().timestamp()
            return data["ticket"]
        else:
            return None

    # 获取森果微信 Access Token
    @classmethod
    def get_client_access_token(cls):  # 微信接口调用所需要的access_token,不需要用户授权
        access_token = redis.get('pf_access_token')
        if access_token:
            return access_token.decode('utf-8')
        else:
            data = json.loads(urllib.request.urlopen(cls.client_access_token_url).read().decode("utf-8"))
            if 'access_token' in data:
                access_token = data['access_token']
                redis.set("pf_access_token",access_token,3600)
                return access_token
            else:
                return None


    # 获取用户是否关注了森果微信公众号
    @classmethod
    def get_user_subcribe(cls,openid):
        access_token = cls.get_client_access_token()
        user_subcribe_url = 'https://api.weixin.qq.com/cgi-bin/user/info?access_token={0}&openid={1}'.format(access_token,openid)
        res = requests.get(user_subcribe_url,headers = {"connection":"close"})
        if type(res.content)== bytes:
            s = str(res.content,'utf-8')
        else:
            s = res.content.decode('utf-8')
        data = json.loads(s)
        json_data = json.dumps(data)
        subscribe = data.get('subscribe')
        return subscribe

    @classmethod
    def createOauthUrlForCode(cls, redirectUrl,scope,state,appid=None,component_appid=None):
        """生成可以获得code的url"""
        urlObj = {}
        if appid:
            urlObj["appid"] = appid
        else:
            urlObj["appid"] = MP_APPID
        urlObj["redirect_uri"] = tornado.escape.url_escape(redirectUrl)
        urlObj["response_type"] = "code"
        urlObj["scope"] = scope
        urlObj["state"] = state
        bizString = cls.formatBizQueryParaMap(urlObj, False)
        # 居然这个参数丢到前面去就不能出来那个授权页面，简直是奇了怪了。FFF
        if component_appid:
            bizString+="&component_appid="+str(component_appid)
        return "https://open.weixin.qq.com/connect/oauth2/authorize?"+bizString+"#wechat_redirect"

    @classmethod
    def getOpenidByComponentAppid(cls,code,appid,component_appid,component_access_token):
        """通过curl向微信提交code，以获取openid"""
        urlObj = {}
        urlObj["code"] = code
        urlObj["appid"] = appid
        urlObj["component_appid"] = component_appid
        urlObj["component_access_token"] = component_access_token
        urlObj["grant_type"] = "authorization_code"
        bizString = cls.formatBizQueryParaMap(urlObj, False)
        url = 'https://api.weixin.qq.com/sns/oauth2/component/access_token?'+bizString
        data = requests.get(url)
        data = data.content.decode("utf-8")
        data = json.loads(data)
        openId = data.get("openid",None)
        access_token = data.get("access_token",None)
        return openId,access_token

    @classmethod
    def getOpenidByAppsecret(cls,code,appid=None,appsecret=None):
        """通过curl向微信提交code，以获取openid"""
        urlObj = {}
        if appid:
            urlObj["appid"] = appid
        else:
            urlObj["appid"] = MP_APPID
        if appsecret:
            urlObj["secret"] = appsecret
        else:
            urlObj["secret"] = MP_APPSECRET
        urlObj["grant_type"] = "authorization_code"
        urlObj["code"] = code
        bizString = cls.formatBizQueryParaMap(urlObj, False)
        url  = 'https://api.weixin.qq.com/sns/oauth2/access_token?'+bizString
        data = requests.get(url)
        data = data.content.decode("utf-8")
        data = json.loads(data)
        openId = data.get("openid",None)
        access_token = data.get("access_token",None)
        return openId,access_token

    def formatBizQueryParaMap(paraMap, urlencode):
        """格式化参数，签名过程需要使用"""
        slist = sorted(paraMap)
        buff = []
        for k in slist:
            v = quote(paraMap[k]) if urlencode else paraMap[k]
            buff.append("{0}={1}".format(k, v))
        return "&".join(buff)

    # 基础支持里面的接口，获取用户信息的。
    # 如果没有关注，只有subscribe，好像也有union_id；如果关注了，就都有
    @classmethod
    def getWxInfo_CGI(cls,openid,access_token):
        userinfo_url = 'https://api.weixin.qq.com/cgi-bin/user/info?access_token={0}&openid={1}'.format(access_token,openid)
        try:
            data = json.loads(urllib.request.urlopen(userinfo_url).read().decode('utf-8'))
        except Exception as e:
            return None
        if "errcode" in data:
            return None
        return data

    # user_info授权里面的接口，获取用户信息。
    # 只有userinfo授权的时候才能调用这个接口
    @classmethod
    def getWxInfo_SNS(cls,openid,access_token):
        userinfo_url = 'https://api.weixin.qq.com/sns/userinfo?access_token={0}&openid={1}&lang=zh_CN'.format(access_token,openid)
        try:
            data = json.loads(urllib.request.urlopen(userinfo_url).read().decode('utf-8'))
        except Exception as e:
            return None
        if "errcode" in data:
            return None
        return data

#########################  end  #############################
#检查openid
class CheckOpenid(object):
    def __init__(self,session,link):
        self.session=session
        self.link=link

    def update_account_from_wxinfo(self,account_info,wx_userinfo):
        headimgurl = wx_userinfo["headimgurl"].replace("http://","https://")
        account_info.sex              = wx_userinfo["sex"]
        account_info.nickname         = wx_userinfo["nickname"]
        account_info.headimgurl       = headimgurl
        account_info.wx_country       = wx_userinfo["country"]
        account_info.wx_province      = wx_userinfo["province"]
        account_info.wx_city          = wx_userinfo["city"]

    # func:检查openid,并更新
    # return:
    #   调用该函数的地方，不跳出，返回----0,''
    #   调用该函数的地方，重定向，返回----1,重定向链接
    #   调用该函数的地方，返回错误，返回----2,出错信息
    def resolve_openid(self,account_info,code,shop_admin,oauth_type):
        openid = account_info.wx_openid
        # 微信浏览器下，如果用户表中现存的openid不正确则重新获取并更新；正确则直接使用，不再重新获取
        if not openid or openid[:6] != OPENID_BEGIN :
            if len(code)<=2:
                # 商户绑定了认证服务号，返回基础授权链接（静默授权）
                if oauth_type==1:
                    path = APP_OAUTH_CALLBACK_URL + self.link
                    url = WxOauth2.createOauthUrlForCode(path,"snsapi_base","123")
                    return 1,url
                # 商户未绑定认证服务号，返回userinfo授权链接
                else:
                    path = APP_OAUTH_CALLBACK_URL + self.link
                    url = WxOauth2.createOauthUrlForCode(path,"snsapi_userinfo","STATE")
                    return 1,url
            else:
                # 根据code得到openid先
                wx_openid,access_token = WxOauth2.getOpenidByAppsecret(code)
                if wx_openid:
                    account_info.wx_openid=wx_openid
                    # 如果商户未绑定认证服务号，通过森果服务号userinfo接口更新用户信息
                    # 如果用户绑定了自己的认证服务号，则不走森果userinfo授权（只走下面的静默授权）
                    if oauth_type!=1:
                        # 根据授权接口里面得到的access_token和openid，得到其他的用户信息
                        wx_userinfo=WxOauth2.getWxInfo_SNS(wx_openid,access_token)
                        if wx_userinfo:
                            self.update_account_from_wxinfo(account_info,wx_userinfo)
                    # 根据基础支持接口的access_token和openid得到union_id
                    access_token = WxOauth2.get_client_access_token()
                    wx_userinfo=WxOauth2.getWxInfo_CGI(wx_openid,access_token)
                    if wx_userinfo:
                        account_info.subscribe=wx_userinfo["subscribe"]
                        account_info.wx_unionid=wx_userinfo["unionid"]
                        self.session.commit()
                    code=""
                else:
                    return 2,"获取用户信息失败，请联系森果客服(senguocc300)"

        #####################获取mp_customer_link###################
        # 商户绑定了自己的公众号
        if oauth_type:
            admin_id = shop_admin.id
            appid    = shop_admin.mp_appid
            has_mp_customer_link = self.session.query(models.Mp_customer_link.id).filter_by(customer_id=account_info.id,mp_appid=appid).first()
            if not has_mp_customer_link:
                sa_access_token = None
                from handlers.openwx import OpenComponent
                open_component = OpenComponent()
                # 自动绑定：需使用ComponentVerifyTicket获取微信openid
                if oauth_type == 1:
                    component_appid = 'wx2be982f79f0a405d'
                    if len(code)<=2:
                        path = 'https://i.senguo.cc' + self.link
                        url = WxOauth2.createOauthUrlForCode(path,"snsapi_userinfo","STATE",appid,component_appid)
                        return 1,url
                    else:
                        ComponentVerifyTicket = redis.get('component_verify_ticket').decode('utf-8')
                        if_success,ret_info = open_component.get_open_component_access_token()
                        if if_success:
                            component_access_token=ret_info
                        else:
                            return 2,ret_info
                        sa_wx_openid,sa_access_token = WxOauth2.getOpenidByComponentAppid(code,appid,component_appid,component_access_token)

                # 非自动绑定：需使用appid与appsecret获取微信openid
                elif oauth_type==2:
                    appsecret = shop_admin.mp_appsecret
                    if len(code)<=2:
                        path = APP_OAUTH_CALLBACK_URL + self.link
                        redirect_uri = tornado.escape.url_escape(path)
                        url = WxOauth2.createOauthUrlForCode(path,"snsapi_base","123",appid)
                        return 1,url
                    else:
                        sa_wx_openid,sa_access_token = WxOauth2.getOpenidByAppsecret(code,appid,appsecret)
                        sa_access_token = None

                if sa_wx_openid:
                    # 如果该用户在对应平台下存有wxopenid则更新，如果没有则生成
                    try:
                        admin_customer_openid = self.session.query(models.Mp_customer_link).filter_by(wx_openid=sa_wx_openid).one()
                        admin_customer_openid.update(session=self.session,customer_id=account_info.id, mp_appid=appid)
                    except:
                        admin_customer_openid = models.Mp_customer_link(customer_id=account_info.id, mp_appid=appid, wx_openid=sa_wx_openid)
                        self.session.add(admin_customer_openid)

                    # 根据基础支持接口的access_token和openid得到并更新用户是否关注的信息
                    if sa_access_token:
                        if not account_info.nickname or account_info.nickname[:2]=="用户":
                            wx_userinfo=WxOauth2.getWxInfo_SNS(sa_wx_openid,sa_access_token)
                            if wx_userinfo:
                                self.update_account_from_wxinfo(account_info,wx_userinfo)
                        auto_access_token = open_component.get_mp_auth_access_token_from_refreshtoken(component_access_token,shop_admin)
                        wx_userinfo=WxOauth2.getWxInfo_CGI(sa_wx_openid,auto_access_token)
                        if wx_userinfo:
                            try:
                                admin_customer_openid.subscribe=wx_userinfo["subscribe"]
                                if not admin_customer_openid.ever_subscribe:
                                    admin_customer_openid.ever_subscribe=wx_userinfo["subscribe"]
                            except:
                                wx_userinfo['time']=str(datetime.datetime.now())
                                wx_userinfo['admin_id']=str(shop_admin.id)
                                wx_userinfo['customer_id']=str(account_info.id)
                                log_msg_dict("get_wxinfo",wx_userinfo)
                    try:
                        self.session.commit()
                    except:
                        self.session.rollback()
        return 0,''

#生成带参数二维码
class WxTicketUrl(object):
    # 生成公众号带参数的二维码
    @classmethod
    def get_ticket_url(self,source="login"):
        '''
            9位留给用户登录
            8位留给微信绑定
        '''
        access_token = WxOauth2.get_client_access_token()
        if source == "login":
            scene_id = self.make_scene_id_len9()
        elif source == "bind":
            scene_id = self.make_scene_id_len8()
        else:
            return

        url = 'https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token={0}'.format(access_token)
        data = {"action_name": "QR_SCENE","expire_seconds":60*60,"action_info": {"scene": {"scene_id": scene_id}}}
        r = requests.post(url,data = json.dumps(data))
        result = json.loads(r.text)
        ticket_url = result.get('url','')
        return ticket_url,scene_id

    @classmethod
    def get_ticket_url_permanent(self,shop_id=None,type=0):
        access_token = WxOauth2.get_client_access_token()
        if shop_id:
            scene_id = int(str(type) + str(shop_id).zfill(6))
        else:
            scene_id = self.make_scene_id()
        url = 'https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token={0}'.format(access_token)
        data = {"action_name": "QR_LIMIT_STR_SCENE","action_info": {"scene": {"scene_str": str(scene_id)}}}
        r = requests.post(url,data = json.dumps(data))
        result = json.loads(r.text)
        ticket_url = result.get('url','')
        return ticket_url,scene_id

    # 以间的随机数生成scene_id，scene_id用于扫码登录时识别用户(9位随机数)
    def make_scene_id_len9():
        '''9位随机数'''
        import random
        while 1:
            scene_id = random.randint(100000000,999999999)
            if not redis.get('pf_scene_openid:%s' % scene_id):
                break
        return scene_id

    def make_scene_id_len8():
        '''8位随机数'''
        import random
        while 1:
            scene_id = random.randint(10000000,99999999)
            if not redis.get('pf_scene_openid:%s' % scene_id):
                break
        return scene_id