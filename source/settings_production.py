# 请勿使用该文件

# cookie域名
ROOT_HOST_NAME = "carrefour.senguo.cc"

TEMPLATE_PATH = "templates"   # 本地模版路径配置
STATIC_PATH_URL = "/static/"

# mysql数据库相关
MYSQL_SERVER = "senguo-master.mysql.rds.aliyuncs.com:3306"
MYSQL_DRIVER        = "mysqlconnector"
MYSQL_USERNAME      = "monk"
MYSQL_PASSWORD      = "Rri9$sW)09z^_2q!"
DB_NAME             = "senguocf"
DB_STATISTIC_NAME   = "senguocf"
# DB_CHARSET        = "utf8mb4"
DB_CHARSET          = "utf8"  # 如果你的电脑不支持utf8mb4，请使用utf8

# redis数据库相关
REDIS_SERVER = "r-bp16b4b9b1bf3854744.redis.rds.aliyuncs.com"
REDIS_PORT   = 6379
REDIS_PASSWORD = "WRfnzrQTc813CUiG"

# celery broker相关
# CELERY_BROKER = "amqp://monk:oWgi7ek0_Szp-0s7@10.165.34.30:5672//"
CELERY_BROKER = "amqp://monk:mRzP7vNB_xu-MZ8o@172.16.0.2:5672//"
# 授权回调域名
APP_OAUTH_CALLBACK_URL = "https://carrefour.senguo.cc"

# 授权回调域名
APP_OAUTH_CALLBACK_URL = "https://carrefour.senguo.cc"

#果蔬批发服务号
# MP_APPID     = "wx554875345d7cbba4"
# MP_APPSECRET = "a2dd069d968f5790c2b2cd491582d8ff"
MP_APPID     = "wx554875345d7cbba4-000000"  # 请务必修改此常量，保证本地不会生成access_token致使线上access_token过期
MP_APPSECRET = "a2dd069d968f5790c2b2cd491582d8ff-000000"  # 请务必修改此常量，保证本地不会生成access_token致使线上access_token过期

#家乐福app(微信开放平台)
# CARREFOUR_APPID     = "waiting"
# CARREFOUR_APPSECRET = "waiting"
CARREFOUR_APPID     = "wxf4a83a0c6dae7477"  # 请务必修改此常量
CARREFOUR_APPSECRET = "27a94ff552b36b60a8bbdfdf881cdcad"   # 请务必修改此常量

# 百度AI开放平台 10464550
BAIDU_APIKEY = 'xZLWgNDVgLRh9iwIA2Xt6yM1'
BAIDU_SECRETKEY = 'HO7m2a7eTGeM9rPfMc73REWy7KwYwSCR'

# 七牛云的参数
ACCESS_KEY       = "Pm0tzHLClI6iHqxdkCbwlSwHWZycbQoRFQwdqEI_"
SECRET_KEY       = "gCjIMVE_lpW7d2bjI-AdMXDKQeE1bdtKxRInBRTH"
BUCKET_SHOP_IMG  = "shopimg"
SHOP_IMG_HOST    = "https://odhm02tly.qnssl.com/"

#　心知天气的参数
XINZHI_KEY		 = "ma7jbrp9dv1cdbea"

# 用于应用之间
API_SECRETKEY = 'oWw}G48n,6Dgf8~+'

# smtp 服务相关参数
SMTP_SERVER = 'smtp.qq.com'
EMAIL_PASSWORD = 'apjkuhinohpwhehf'
EMAIL_SENDER = '1593674921@qq.com'
EMAIL_RECEIVERS = ["1593674921@qq.com"]
EMAIL_SUBJECT='家乐福果蔬管理系统统计数据报表'
EMAIL_BODY='详情见附件！'
