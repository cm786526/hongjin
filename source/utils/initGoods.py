import sys
sys.path.append('../')
import xlrd
import xlwt
import dal.models as models
session = models.DBSession()
import datetime,time
import requests
import json
from dal.area import dis_dict3 as area_dict
from settings import XINZHI_KEY
from dal.holiday_dict import holiday_dict

def parse_xls_and_insert_to_database(path, filename,classify):
    """ 解析excel文件，解析出满足导入基本条件的数据并插入到数据库中

    :参数 path: 目标文件的存放路径
    :参数 filename: 通常会以shop_id来进行命名
    :参数 classify: 商品分类
    :返回值:
    """
    xlrd.Book.encoding = "gbk"
    xls_workbook = xlrd.open_workbook("{}{}.xlsx".format(path, filename))
    table = xls_workbook.sheets()[0]
    nrows = table.nrows
    print(nrows,"111")
    for i in range(1, nrows):
        row = table.row_values(i)
        goods_code, goods_name,unit= row
        if unit.find("kg(千克)") !=-1 :
            new_unit =1
        else:
            new_unit =2
        new_goods = models.Goods(goods_code=int(goods_code),goods_name=goods_name,unit=new_unit,classify=classify)
        session.add(new_goods)
    session.commit()
    return True


def parse_xls_and_insert_to_database_shop(path, filename):
    """ 解析excel文件，解析出满足导入基本条件的数据并插入到数据库中

    :参数 path: 目标文件的存放路径
    :参数 filename: 通常会以shop_id来进行命名
    :参数 classify: 商品分类
    :返回值:
    """
    xlrd.Book.encoding = "gbk"
    xls_workbook = xlrd.open_workbook("{}{}.xlsx".format(path, filename))
    table = xls_workbook.sheets()[0]
    nrows = table.nrows
    Goods = models.Goods
    fruit_count = session.query(Goods).filter(Goods.status!=-1).filter_by(classify=1).count()
    vegetables_count = session.query(Goods).filter(Goods.status!=-1).filter_by(classify=2).count()
    for i in range(1, nrows):
        row = table.row_values(i)
        shop_province, shop_city,shop_name,shop_region,shop_city_carrefour= row
        new_shop = models.Shop(shop_province=shop_province,\
                                shop_city=shop_city,\
                                shop_name=shop_name,\
                                shop_region=shop_region,\
                                shop_city_carrefour=shop_city_carrefour,\
                                admin_id=1,\
                                fruit_count=fruit_count,\
                                vegetables_count=vegetables_count)
        session.add(new_shop)
    session.commit()
    return True

#添加超级管理员
def add_super_admin(phone):
    Accountinfo=models.Accountinfo
    Shop=models.Shop
    new_super_admin = Accountinfo(phone=phone)
    session.add(new_super_admin)
    session.flush()
    #每当有一个新用户注册的时候，就要对应的增加录入设置的信息
    Accountinfo.init_recorder_settings(session,new_super_admin.id)
    session.commit()
    return True

# 对应增加管理员信息,超级管理员应该要管理所有店铺　
def add_hire_link():
    HireLink=models.HireLink
    Shop=models.Shop
    all_shop=session.query(Shop).all()
    for shop in all_shop:
        hire_link = HireLink(staff_id =1,active_admin=1,shop_id=shop.id)
        session.add(hire_link)
        session.flush()
    session.commit()

# 更新当前日期的天气信息
def update_current_weather():
    Shop=models.Shop
    HistoryWeatherRecord=models.HistoryWeatherRecord
    all_citys=session.query(Shop.shop_city).distinct().all()
    all_citys_code=[]
    for city in all_citys:
        all_citys_code.append(city.shop_city)
    current_date=datetime.date.today()
    current_weekday=current_date.weekday()
    result=requests.get('http://www.easybots.cn/api/holiday.php?d='+str(current_date))
    try:
        result = json.loads(result.content.decode("utf-8"))
    except:
        print("update_current_weather failed")
        return False
    current_date=str(current_date).replace('-','')
    holiday="无"
    if str(current_date) in holiday_dict:
        holiday=holiday_dict[current_date]
    elif current_weekday in [5,6]:
        holiday="周末"
    city_list=area_dict["city_list"]
    country_list=area_dict["country_list"]
    failed_count=0
    for city_code in all_citys_code:
        city_name=""
        str_city_code=str(city_code)
        if str_city_code in city_list:
            city_name=city_list[str_city_code]
        elif str_city_code in country_list:
            city_name=country_list[str_city_code]
        # 请求天气数据
        result=requests.get('https://api.seniverse.com/v3/weather/daily.json?key='+\
                            XINZHI_KEY+'&location='+city_name+'&language=zh-Hans&unit=c&start=0&days=１')
        if result.status_code != 200:
            failed_count+=1
            continue
        result=json.loads(result.content.decode("utf-8"))
        result=result["results"][0]["daily"][0]
        new_weather = HistoryWeatherRecord(city_code=city_code,\
                                            city_name=city_name,\
                                            create_date=current_date,\
                                            low_temperature=result["low"],\
                                            high_temperature=result["high"],\
                                            weather=result["text_day"],\
                                            week_day=current_weekday,\
                                            holiday=holiday)
        session.add(new_weather)
    session.commit()
    print("共计%d个城市或者区域的天气信息没有找到"%failed_count)
    return True

# 给店铺添加商品的脚本
def add_goods_for_shop():
    Shop=models.Shop
    Goods=models.Goods
    ShopGoods=models.ShopGoods
    all_shops=session.query(Shop).all()
    all_goods=session.query(Goods).all()
    for each_shop in all_shops:
        for each_goods in all_goods:
            new_shop_goods=ShopGoods(shop_id=each_shop.id,goods_id=each_goods.id)
            session.add(new_shop_goods)
    session.commit()
    return True

# 给店铺区域增加水果和蔬菜的预订系数
def add_reserve_ratio():
    Shop=models.Shop
    ReserveRatio=models.ReserveRatio
    all_regions=session.query(Shop.shop_region).distinct(Shop.shop_region).all()
    for each_region in all_regions:
        new_reserve_ratio=ReserveRatio(goods_classify=1,region=each_region[0].strip(),ratio_value=1)
        session.add(new_reserve_ratio)
        new_reserve_ratio=ReserveRatio(goods_classify=2,region=each_region[0].strip(),ratio_value=1)
        session.add(new_reserve_ratio)
    session.commit()
    return True

if __name__ == "__main__":
    # 初始化数据库
    models.init_db_data()
    # #添加超级管理员
    # if add_super_admin("18627163362"):
    #     print("init add_super_admin success!")
    # #插入水果
    # if parse_xls_and_insert_to_database("./","fruit",1):
    #     print("init fruit database success!")
    # #插入蔬菜
    # if parse_xls_and_insert_to_database("./","vege",2):
    #     print("init vegetables database success!")
    # #插入店铺
    # if parse_xls_and_insert_to_database_shop("./","store"):
    #     print("init stores database success!")
    # #插入当天的天气信息
    # if update_current_weather():
    #     print("init weather database success!")
    # # 对应增加管理员信息,超级管理员应该要管理所有店铺　
    # add_hire_link()

    # #给店铺增加商品
    # if add_goods_for_shop():
    #     print("店铺商品初始化成功！")

    # # 给店铺区域增加水果和蔬菜的预订系数
    # if add_reserve_ratio():
    #     print("增加水果和蔬菜的预订系数成功！")
