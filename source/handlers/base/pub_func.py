import json
import hashlib
import requests
import datetime,time
import re

from sqlalchemy import func

import dal.models as models
from dal.db_configs import redis

#时间
class TimeFunc():
    @classmethod
    def get_date_split(cls,choose_datetime):
        t_year = choose_datetime.year
        t_month = choose_datetime.month
        t_day = choose_datetime.day
        t_week = int(choose_datetime.strftime('%W'))
        return t_year,t_month,t_day,t_week

    @classmethod
    def get_date(cls,choose_datetime):
        return choose_datetime.strftime('%Y%m%d')

    @classmethod
    def get_time(cls,choose_datetime):
        return choose_datetime.strftime('%H:%M:%S')

    # 将时间类型换为时间字符串
    @classmethod
    def time_to_str(self, time, _type="all"):
        if _type == "all":
            fromat = "%Y-%m-%d %H:%M:%S"
        elif _type == "date":
            fromat = "%Y-%m-%d"
        elif _type == "hour":
            fromat = "%H:%M"
        elif _type == "month":
            fromat = "%m-%d"
        elif _type == "year":
            fromat = "%Y-%m"
        elif _type == "full":
            fromat = "%Y%m%d%H%M"
        elif _type =="no_year":
            fromat = "%m-%d %H:%M:%S"
        elif _type =="time":
            fromat = "%H:%M:%S"
        else:
            fromat = "%Y-%m-%d %H:%M"
        try:
            time_res = time.strftime(fromat)
        except:
            time_res = ""
        return time_res

    #根据参数时间所在周的开始时间
    def getweekfirstday(current_date):
        yearnum=current_date.year
        weeknum=int(current_date.strftime("%W"))
        daynum=int(current_date.weekday())+1

        yearstart = datetime.datetime(yearnum,1,1)
        yearstartweekday = int(yearstart.weekday())+1
        if yearstartweekday < int (daynum):
            daydelat = (7-int(yearstartweekday))+(int(weeknum))*7
        else:
            daydelat = (7-int(yearstartweekday))+(int(weeknum)-1)*7
        a = yearstart+datetime.timedelta(days=daydelat+1)
        return a

    # 获取fake清算状态
    # 已清算状态不用重新更新，待清算和清算中的状态，把对应日期传进来，然后检查对应日期和今天截头不去尾,如果没有工作日,那就仍然是待清算状态，如果有一个工作日，就是清算中状态，如果有两个，就是已清算了。
    @classmethod
    def get_fake_clearing_state(cls,the_date):
        delta_day = (datetime.datetime.combine(datetime.datetime.now(),datetime.time.min)-datetime.datetime.combine(the_date,datetime.time.min)).days
        fake_clearing_state = 0
        for i in range(delta_day):
            temp_day = (the_date + datetime.timedelta(i+1)).strftime('%Y-%m-%d')
            if holiday_tag[temp_day]==0:
                fake_clearing_state+=1
                if fake_clearing_state == 2:
                    break
        return fake_clearing_state

    #获取当天的开始时间
    @classmethod
    def get_day_start_time(cls):
        now_time = datetime.datetime.now()
        start_time = datetime.datetime(now_time.year,now_time.month,now_time.day)
        return start_time

    #获取XX天的日期
    @classmethod
    def get_date_list(cls,date_range=7,date_type="day"):
        date_now=datetime.datetime.now()
        date_list = []
        current_month_first_day = 0
        for i in range(date_range):
            if date_type == "day":
                date = date_now-datetime.timedelta(days=i)
                date = date.date()
            else:
                date = cls.get_date_month(date_now,i)
            date_list.append(date)
        date_list.reverse()
        return date_list

    #获取XX月的月份
    @classmethod
    def get_date_month(cls,date,range_num):
        year = date.year
        month = date.month
        if month - range_num<= 0:
            res_month = 12+(month - range_num)
            res_year = year-1
        else:
            res_month = month-range_num
            res_year = year
        date = "%d-%d"%(res_year,res_month)
        return date

    #获取xx天的日期
    @classmethod
    def get_assign_date(cls,days=0):
        now_date = datetime.datetime.now()
        assign_date = datetime.datetime(now_date.year,now_date.month,now_date.day)-datetime.timedelta(days=days)
        return assign_date

    #拼接时间字符串
    @classmethod
    def splice_time(cls,year,month,day,time):
        time = "{year}-{month}-{day} {time}".format(year=year,month=month,day=day,time=cls.time_to_str(time,"time"))
        return time

    #获取今天的date类型
    @classmethod
    def get_today_date(cls):
        return datetime.date.today()

    # 获取今天的datetime类型
    @classmethod
    def get_today_datetime(cls):
        return datetime.datetime.combine(datetime.datetime.now(),datetime.time.min)

    # 获取两个日期之间的周数差，计算方式为 date2 - date1
    @staticmethod
    def week_difference(date1, date2):
        monday1 = (date1 - datetime.timedelta(date1.weekday()))
        monday2 = (date2 - datetime.timedelta(date2.weekday()))
        return (monday2 - monday1).days / 7

    # 获取两个日期之间的月数差，计算方式为 date2 - date1
    @staticmethod
    def month_difference(date1, date2):
        return (date2.year - date1.year) * 12 + date2.month - date1.month

    # 根据给定日期获取该日期所在周的开始时间和下周开始时间
    @staticmethod
    def get_week_start_end(date):
        dayscount = datetime.timedelta(days=date.isoweekday())
        dayfrom = date - dayscount + datetime.timedelta(days=1)
        dayto = date - dayscount + datetime.timedelta(days=8)
        return dayfrom,dayto
    # 根据给定日期获取该日期所在月的开始时间和下个月的开始时间
    @staticmethod
    def get_month_start_end(date):
        day_begin = datetime.date(date.year, date.month,1)                   # 月初肯定是1号
        day_end = datetime.date(date.year, date.month+1,1)                   # 下个月１号
        return day_begin,day_end
#字符
class CharFunc():
    # 检查是否包含汉字
    @classmethod
    def check_contain_chinese(cls,check_str):
        for ch in check_str:
            if '\u4e00' <= ch <= '\u9fff':
                return True
        return False

    #检查汉字字符个数
    @classmethod
    def get_contain_chinese_number(cls,check_str):
        number = 0
        for ch in check_str:
            if '\u4e00' <= ch <= '\u9fff' or ch=="：":
                number += 1
        return number

#数字
class NumFunc():
    # 处理金额小数位数（1.00处理为1; 1.10处理为1.1; 1.111处理为1.11; 非数字返回0）
    @classmethod
    def check_float(cls,number,place=2):
        try:
            num = round(float(number),place)
        except:
            num = 0
        if num == int(num):
            num = int(num)
        return num

    # 将数字处理为整数（非数字返回0）
    @classmethod
    def check_int(cls,number):
        try:
            num = int(number)
        except:
            num = 0
        return num

    # 将阿拉伯数字转为中文大写
    @classmethod
    def upcase_number(cls,n):
        units = ['', '万', '亿']
        nums = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
        decimal_label = ['角', '分']
        small_int_label = ['', '拾', '佰', '仟']
        int_part, decimal_part = str(int(n)), str(cls.check_float(n - int(n)))[2:]  # 分离整数和小数部分
        res = []
        if decimal_part:
            decimal_tmp = ''.join([nums[int(x)] + y for x, y in list(zip(decimal_part, decimal_label))])
            decimal_tmp=decimal_tmp.replace('零角', '零').replace('零分', '')
            res.append(decimal_tmp)

        if not decimal_part:
            res.append('整')

        if int_part != '0':
            res.append('圆')
            while int_part:
                small_int_part, int_part = int_part[-4:], int_part[:-4]
                tmp = ''.join([nums[int(x)] + (y if x != '0' else '') for x, y in list(zip(small_int_part[::-1], small_int_label))[::-1]])
                tmp = tmp.rstrip('零').replace('零零零', '零').replace('零零', '零')
                unit = units.pop(0)
                if tmp:
                    tmp += unit
                    res.append(tmp)
        if int_part == '0' and not decimal_part:
            res.append('零圆')
        return ''.join(res[::-1])

    # 按精度设置规则对金额进行处理
    # precision:精度设置 1:到分 2:到角 3:到元
    # precision_type:精度方式 1:四舍五入 2:抹掉尾数 3:进一法
    @classmethod
    def handle_precision(cls,in_money,precision,precision_type):
        in_money_cent = int(round(in_money*100))
        if precision==1:
            return in_money_cent
        else:
            # 整数部分
            int_part = cls.check_int(str(in_money_cent)[:-2])
            # 十分位
            tenths_digit_part = cls.check_int(str(in_money_cent)[-2:-1])
            # 百分位
            percentile_part = cls.check_int(str(in_money_cent)[-1:])
            if precision==2:
                # (四舍五入并且百分位大于等于5)或者(进一法并且百分位大于等于1)
                if (precision_type == 1 and percentile_part>=5) or (precision_type == 3 and percentile_part>=1):
                    return int_part*100+(tenths_digit_part+1)*10
                else:
                    return int_part*100+(tenths_digit_part)*10
            else:
                # (四舍五入并且十分位大于等于5)或者(进一法并且十分位大于等于1)
                if (precision_type == 1 and tenths_digit_part>=5) or (precision_type == 3 and tenths_digit_part>=1):
                    return (int_part+1)*100
                else:
                    return int_part*100
check_float = NumFunc.check_float


#转换数据格式
class DataFormatFunc():

    @classmethod
    def format_str_to_int_inlist(cls,data_list):
        res_list = []
        for data in data_list:
            try:
                data = int(data)
            except:
                continue
            res_list.append(data)
        return res_list

    @classmethod
    def format_int_to_str_inlist(cls,data_list):
        res_list = []
        for data in data_list:
            try:
                data = int(data)
            except:
                continue
            data = str(data)
            res_list.append(data)
        return res_list

    @classmethod
    def split_str(cls,string,symbol=","):
        return string.split(symbol)

    @classmethod
    def join_str(cls,string,symbol=","):
        return symbol.join(string)


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


#省份城市转换
class ProvinceCityFunc():
    @classmethod
    def city_to_province(cls,code):
        from dal.dis_dict import dis_dict
        province_code = int(code/10000)*10000
        if dis_dict.get(province_code,None):
            return province_code
        else:
            return None

    @classmethod
    def county_to_province(cls,code):
        from dal.dis_dict import dis_dict
        province_code = int(code/10000)*10000
        if dis_dict.get(province_code,None):
            return province_code
        else:
            return None

    @classmethod
    def get_city(cls,code):
        from dal.dis_dict import dis_dict
        try:
            if "city" in dis_dict[int(code/10000)*10000].keys():
                text = dis_dict[int(code/10000)*10000]["city"][code]["name"]
            else:
                text = ""
        except:
            text = ""
        return text

    @classmethod
    def get_province(cls,code):
        from dal.dis_dict import dis_dict
        try:
            text = dis_dict.get(int(code),{}).get("name",'')
        except:
            text = ""
        return text
#qury的结果转换成字典
class QuryListDictFunc():
    @classmethod
    def convert_list_to_dict(cls,keyword_list,data_list):
        new_data_list=[]
        for each_data in data_list:
            dict_temp={}
            for key in keyword_list:
                dict_temp[key]=eval("each_data.%s"%key)
            new_data_list.append(dict_temp)
        return  new_data_list

class PubMethod():
    """双端共用的一些方法
    """
    @classmethod
    def get_all_shops(cls,session,current_user_id):
        """ 获取当前管理员管理的所有店铺
        """
        Shop=models.Shop
        HireLink=models.HireLink
        hire_links=session.query(HireLink)\
                            .filter_by(staff_id=current_user_id,\
                                active_admin=1)\
                            .all()
        admin_shop_id_list=[]
        for each_hire_link in hire_links:
            admin_shop_id_list.append(each_hire_link.shop_id)
        all_shops=session.query(Shop)\
                            .filter(Shop.id.in_(admin_shop_id_list))\
                            .all()
        keyword=["id","shop_name"]
        shop_ids=[x.id for x in all_shops]
        shop_list=QuryListDictFunc.convert_list_to_dict(keyword,all_shops)
        return shop_list,shop_ids