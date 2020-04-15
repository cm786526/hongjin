# models.py
from sqlalchemy import func, ForeignKey, Column, Index,Float
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import String, Integer, DateTime,Date
from dal.db_configs import MapBase,redis, DBSession
from libs.senguo_encrypt import SimpleEncrypt
class _CommonApi:
    def save(self, session):
        s = session
        s.add(self)
        s.commit()

    def update(self, session, **kwargs):
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])
        self.save(session)

    @classmethod
    def get_or_create_instance(cls,session,**kwargs):
        the_instance = session.query(cls).filter_by(**kwargs).first()
        if not the_instance:
            the_instance=cls(**kwargs)
            session.add(the_instance)
            session.flush()
            if_add=True
        else:
            if_add=False
        return if_add,the_instance


class _AccountApi(_CommonApi):

    @classmethod
    def get_by_id(cls, session, id):
        s = session
        try:
            u = s.query(cls).filter_by(id=id).one()
        except:
            u = None
        return u

    @classmethod
    def get_pwd_token(cls, session, id):
        user_pwd_token_key='user_pwd_token:%d'%id
        if redis.get(user_pwd_token_key):
            token = redis.get(user_pwd_token_key).decode()
        else:
            try:
                token = session.query(Accountinfo.password).filter_by(id=id).scalar()[24:48]
            except:
                token = ""
        return token

# shop封装一层,便于测试
class ShopMarket(MapBase,_CommonApi):
    __tablename__ = "shop_market"
    id                  = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    market_name         = Column(String(128),nullable=False,default="")                                    # 市场名称

# 拼接图片域名
class AddImgDomain():
    @classmethod
    def add_domain(cls,img):
        """给图片添加图床域名"""
        if img and img[:1]!="/" and img[:5]!="https":
            return SHOP_IMG_HOST + img
        else:
            return img

    @classmethod
    def add_domain_muti(cls,imgs):
        """传入一个iterable对象，同时给多张图片添加图床域名"""
        imgs_list = []
        if imgs:
            for img in imgs:
                img = cls.add_domain(img)
                imgs_list.append(img)
        return imgs_list

    @classmethod
    def add_domain_headimg(cls,img):
        """为头像添加图床域名，返回 480x480 尺寸的头像"""
        if not img:
            return "/static/common/img/person.png"
        elif img[-4:]=="/132":
            return img[:-3] + "0"
        elif img[-2:]=="/0":
            return img
        else:
            return SHOP_IMG_HOST + img + "?imageView2/1/w/480/h/480"

    @classmethod
    def add_domain_headimgsmall(cls,img):
        """为头像添加图床域名，返回 100x100 尺寸的头像"""
        if not img:
            return "/static/common/img/person.png"
        elif img[-2:]=="/0":
            return img[:-1] + "132"
        elif img[-4:]=="/132":
            return img
        else:
            return SHOP_IMG_HOST + img + "?imageView2/1/w/100/h/100"

    @classmethod
    def add_domain_shop(cls,img):
        """为店铺图片添加图床域名"""
        return cls.add_domain(img) or "/static/images/shop_picture.png"

class Accountinfo(MapBase, _AccountApi):
    """用户的基本信息表
    """
    __tablename__ = "account_info"

    id = Column(Integer, primary_key=True, nullable=False,autoincrement=True)
    phone      = Column(String(32), unique = True)                    # 手机号
    email      = Column(String(64), unique = True)                    # E-mail
    password   = Column(String(128), default = None)                  # 密码（密文）
    sex        = Column(TINYINT, nullable=False, default=0)           # 用户性别 0:未知 1:男 2:女
    nickname   = Column(String(64), default="")                       # 用户昵称
    realname   = Column(String(128))                                  # 用户真实姓名
    headimgurl = Column(String(1024))                                 # 用户头像
    wx_unionid = Column(String(64), unique = True)                    # 微信unionid
                                                                        # 如果开发者拥有多个移动应用、网站应用和公众帐号，
                                                                        # 可通过获取用户基本信息中的unionid来区分用户的唯一性，
                                                                        # 因为同一用户，对同一个微信开放平台下的不同应用
                                                                      #（移动应用、网站应用和公众帐号），unionid是相同的。
    wx_openid   = Column(String(64), default="")                      # 微信openid
    wx_country  = Column(String(32), default="")                      # 用户所在国家
    wx_province = Column(String(32), default="")                      # 用户所在省份
    wx_city     = Column(String(32), default="")                      # 用户所在城市

    beta_code = Column(String(32), unique = True)                     # 内测码
    create_time = Column(DateTime,nullable=False, default=func.now()) # 创建时间

    @property
    def sex_text(self):
        sex_list={0:"未知",1:"男",2:"女"}
        return sex_list.get(self.sex,"未知")

    @property
    def head_imgurl(self):
        return AddImgDomain.add_domain_headimg(self.headimgurl)

    @property
    def head_imgurl_small(self):
        return AddImgDomain.add_domain_headimgsmall(self.headimgurl)

    # 微信登录API
    @classmethod
    def login_by_unionid(cls, session, wx_unionid):
        s = session
        try:
            u = s.query(cls).filter(
                Accountinfo.id==cls.id,
                Accountinfo.wx_unionid==wx_unionid).one()
        except NoResultFound:
            u = None
        return u

    # 手机号或邮箱密码登录
    @classmethod
    def login_by_phone_password(cls, session, phone, password):
        if not phone or not password:
            return None
        try:
            u = session.query(Accountinfo).filter_by(phone = phone, password = password).one()
        except NoResultFound:
            u = None
        if not u:
            try:
                u = session.query(Accountinfo).filter_by(email = phone, password = password).one()
            except NoResultFound:
                u = None
        return u
    #每当有一个新用户注册的时候，就要对应的增加录入设置的信息
    @classmethod
    def init_recorder_settings(cls,session,staff_id):
        record_settings=RecordSettings(staff_id=staff_id)
        session.add(record_settings)
        session.flush()

    # 手机注册API（注意）
    @classmethod
    def register_with_phone(cls, session, phone):
        try:
            account_info = Accountinfo(
                phone  = phone
            )
            session.add(account_info)
            session.flush()
            return account_info
        except:
            session.rollback()
            return None

    # 微信注册API（注意）
    @classmethod
    def register_with_wx(cls, session, wx_userinfo):
        # 判断是否在本账户里存在该用户
        u = cls.login_by_unionid(session, wx_userinfo["unionid"])
        if u:
            # 已存在用户，则更新微信信息
            cls.update_through_wx(session,wx_userinfo,u,action="update")

            # # 使用PC微信扫码登录时不更新openid（非oA打头的）
            # old = u.wx_openid
            # old_start = old[0:2] if old else ''
            # if old_start != "oA":
            #     start = wx_userinfo['openid'][0:2]
            #     if start == "oA":
            #         u.wx_openid = wx_userinfo["openid"]
            session.commit()
            return u
        else:
            # 基本账户中不存在，先创建基本信息，再添加到该用户账户中去
            try:
                u=cls.add_through_wx(session,wx_userinfo)
                session.commit()
                return u
            except:
                session.rollback()
                return None

    @classmethod
    def add_through_wx(cls,session,wx_userinfo):
        headimgurl = wx_userinfo.get("headimgurl",None)
        if headimgurl:
            headimgurl = headimgurl.replace("http://","https://")
        account_info = Accountinfo(
            wx_unionid  = wx_userinfo.get("unionid",None),
            wx_openid   = wx_userinfo.get("openid",None),
            wx_country  = wx_userinfo.get("country",None),
            wx_province = wx_userinfo.get("province",None),
            wx_city     = wx_userinfo.get("city",None),
            headimgurl  = headimgurl,
            nickname    = wx_userinfo.get("nickname",None),
            sex         = wx_userinfo.get("sex",None)
            )
        session.add(account_info)
        session.flush()
        return account_info

    @classmethod
    def update_through_wx(cls,session,wx_userinfo,account,action="update"):
        headimgurl = wx_userinfo.get("headimgurl",None)
        if headimgurl:
            headimgurl = headimgurl.replace("http://","https://")
        if action == "bind":
            account.wx_unionid = wx_userinfo.get("unionid",None)
        if action in ["bind","update_all"]:
            account.wx_openid = wx_userinfo.get("openid",None)
        account.wx_country       = wx_userinfo.get("country",None)
        account.wx_province      = wx_userinfo.get("province",None)
        account.wx_city          = wx_userinfo.get("city",None)
        account.headimgurl       = headimgurl
        account.nickname         = wx_userinfo.get("nickname",None)
        account.sex              = wx_userinfo.get("sex",None)

    @classmethod
    def create_temp_name(cls):
        from random import Random
        chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        random = Random()
        temp_name = ""
        for i in range(9):
            temp_name += chars[random.randint(0,len(chars)-1)]
        return temp_name

# 验证码用途
class VerifyCodeUse:
    # 非登录状态获取验证码用途
    login_verify_code_use = {
        'login': '登录家乐福管理系统账户',
        'register': '注册家乐福管理系统账户',
        'bind': '家乐福管理系统账户绑定手机号',
        'shop_register': '注册店铺',
    }
    # 登录用户获取验证码用途
    operation_verify_code_use = {
        'modify_password': '修改账户密码',
        'shopauth': '申请店铺认证',
        'ownpayment': '申请在线支付渠道',
    }

    @classmethod
    def get_use_text(cls, key, t='all'):
        """获取验证码用途文本

        输入参数
        key 验证码用途标志
        t 验证码用途类别，默认为'all'表示所有，可以取'login'和'operation'

        返回值
        验证码类别文本或None
        """
        if t == 'all':
            all_verify_code_use = cls.login_verify_code_use.copy()
            all_verify_code_use.update(cls.operation_verify_code_use)
            return all_verify_code_use.get(key)
        elif t == 'login':
            return cls.login_verify_code_use.get(key)
        elif t == 'operation':
            return cls.operation_verify_code_use.get(key)
        else:
            return None

# 商品
class Goods(MapBase, _CommonApi):
    __tablename__= "goods"
    id            = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    goods_name    = Column(String(50),nullable=False,default="")              # 商品名称
    goods_code    = Column(String(50),nullable=False,default="")              # 商品编码
    classify      = Column(TINYINT,nullable=False, default=1)                 # 商品分类  1：水果 2：蔬菜
    unit          = Column(Integer,nullable=False,default=1)                  # 库存单位  1: kg  2: pcs
    status        = Column(TINYINT,nullable=False,default=1)                  # 商品状态  1：正常 -1：删除
    market_id     = Column(Integer,ForeignKey(ShopMarket.id),nullable=False,default=0)                  # 市场id
    @property
    def unit_text(self):
        unit_list={1:"kg",2:"PCS"}
        return unit_list.get(self.unit,"未知")

#门店
class Shop(MapBase, _CommonApi):
    __tablename__         = "shop"
    id                    = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    admin_id              = Column(Integer, ForeignKey(Accountinfo.id), nullable=False)           # 店铺超级管理员ID
    shop_name             = Column(String(50),nullable=False,default="")                          # 商品名称
    shop_trademark_url    = Column(String(256), nullable=False, default="")                       # 店铺Logo
    # 店铺地址
    shop_province         = Column(Integer, nullable=False, default =0)                           # 省份
    shop_city             = Column(Integer, nullable=False, default =0)                           # 城市
    shop_region           = Column(String(50),nullable=False,default="")                          # 店铺区域
    shop_city_carrefour   = Column(String(50),nullable=False,default="")                          # 家乐福的城市分区
    fruit_count           = Column(Integer,nullable=False,default=0)                              # 水果数量
    vegetables_count      = Column(Integer,nullable=False,default=0)                              # 蔬菜数量
    market_id             = Column(Integer,ForeignKey(ShopMarket.id),nullable=False,default=0)    # 市场id

#商品门店对应关系
class ShopGoods(MapBase,_CommonApi):
    __tablename__         = "shop_goods"
    id                    = Column(Integer,primary_key=True,nullable=False,autoincrement=True)
    shop_id               = Column(Integer,ForeignKey(Shop.id),nullable=False)                    # 店铺id
    goods_id              = Column(Integer,ForeignKey(Goods.id),nullable=False)                   # 商品id
    status                = Column(TINYINT,nullable=False,default=1)                              # 店铺拥有商品状态，1：正常　－１：删除
    create_date           = Column(DateTime,nullable=False,default=func.now())                    # 添加商品时间
    reserve_ratio         = Column(Float,nullable=False,default=1)                                # 预订量系数
    reserve_cycle         = Column(Integer,nullable=False,default=1)                              # 预订周期

#雇佣关系
class HireLink(MapBase, _CommonApi):
    __tablename__ = "hire_link"
    id                 = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    staff_id           = Column(Integer, ForeignKey(Accountinfo.id))
    shop_id            = Column(Integer,ForeignKey(Shop.id))                                      # 所属店铺id
    admin_permission   = Column(String(512),nullable = False,default='[1,2,3,4]')                 # 管理员权限
    active_admin       = Column(TINYINT,nullable=False,default=0)                                 # 是否是管理员 0：不是 1：是
    active_recorder    = Column(TINYINT,nullable=False,default=0)                                 # 是否是录入员 0：不是 1：是
    create_date        = Column(DateTime,nullable=False,default=func.now())                       # 创建时间
    remarks            = Column(String(512),nullable=False,default="")                            # 备注

#要货需求
class Demand(MapBase, _CommonApi):
    __tablename__ = "demand"
    id                  = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    shop_id             = Column(Integer, ForeignKey(Shop.id),nullable=False,default=0)             # 店铺id
    goods_id            =  Column(Integer,ForeignKey(Goods.id),nullable=False,default=0)            # 商品id
    order_amount        = Column(Float, nullable=False, default=0)                                  # 订货量
    yesterday_wasted    = Column(Float, nullable=False, default=0)                                  # 昨日损耗
    yesterday_sale      = Column(Float, nullable=False, default=0)                                  # 昨日销量
    today_arrival       = Column(Float, nullable=False, default=0)                                  # 今日到货
    today_purchase_price= Column(Integer, nullable=False, default=0)                                # 今日进价
    today_price         = Column(Integer, nullable=False, default=0)                                # 今日售价
    current_stock       = Column(Float, nullable=False, default=0)                                  # 当前库存
    opretor_id          = Column(Integer, ForeignKey(Accountinfo.id),nullable=False,default=0)      # 操作员id
    create_date         = Column(DateTime, nullable=False, default=func.now())                      # 创建时间
    current_date        = Column(Date, nullable=False, default=func.curdate())                      # 当前日期

#录入员设置
class RecordSettings(MapBase, _CommonApi):
    __tablename__ = "record_settings"
    id                  = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    staff_id            = Column(Integer,ForeignKey(Accountinfo.id),nullable=False,default=0)      # 员工id
    order_ratio         = Column(Float,nullable=False,default=1)                                   # 预订量系数

#历史天气记录
class HistoryWeatherRecord(MapBase, _CommonApi):
    __tablename__ = "history_weather_record"
    id                  = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    city_code           = Column(Integer,nullable=False,default=0)                                 # 城市id
    city_name           = Column(String(50),nullable=False,default="")                             # 城市名称
    create_date         = Column(Date,nullable=False,default=func.now())                           # 天气日期
    week_day            = Column(Integer,nullable=False,default=0)                                  # 周几
    low_temperature     = Column(Integer,nullable=False,default=0)                                  # 最低气温
    high_temperature    = Column(Integer,nullable=False,default=0)                                  # 最高气温
    weather             = Column(String(20),nullable=False,default="")                              # 天气
    holiday             = Column(String(20),nullable=True,default="")                               #　节日
    @property
    def weekday_text(self):
        week_list={0:"周一",1:"周二",2:"周三",3:"周四",4:"周五",5:"周六",6:"周日"}
        return week_list.get(self.week_day,"周一")

# 数据库初始化
def init_db_data():
    MapBase.metadata.create_all()
    print("init db success")
    return True
