from sqlalchemy import or_, func
import datetime
from dal.db_configs import redis
import dal.models as models
import dal.models_statistic as models_statistic
from handlers.base.pub_func import TimeFunc


class Statistic():

    @classmethod
    def update_by_day(cls,session,statistic_session,start_datetime):
        """ 按天更新统计数据
        """
        StatisticsDemand=models_statistic.StatisticsDemand
        Demand=models.Demand
        start_date=datetime.date(start_datetime.year,start_datetime.month,start_datetime.day)
        all_demands=session.query(Demand.shop_id,Demand.goods_id,\
                                  func.sum(Demand.order_amount),\
                                  func.max(Demand.yesterday_wasted),\
                                  func.max(Demand.yesterday_sale),\
                                  func.sum(Demand.today_arrival),\
                                  func.sum(Demand.today_purchase_price),\
                                  func.sum(Demand.today_price),\
                                  func.sum(Demand.current_stock),\
                                  func.count(Demand.id),\
                                  func.max(Demand.create_date),\
                                  Demand.current_date)\
                            .order_by(Demand.current_date)\
                            .filter(Demand.current_date>=start_date)\
                            .group_by(Demand.shop_id,Demand.goods_id,Demand.current_date)\
                            .all()
        if not all_demands:
            return True
        for each_demand in all_demands:
            average_purchase_price=0
            average_price=0
            demand_count=each_demand[9]
            if demand_count:
                average_purchase_price=each_demand[6]/demand_count
                average_price=each_demand[7]/demand_count

            # 如果当前的日期统计记录已经存在，则继续累加，否则，添加一条新的记录
            new_statistic_demand=None
            if_new=False
            if each_demand[11]==start_date:
                exist_statistic_demand=statistic_session.query(StatisticsDemand)\
                                                        .filter_by(statistic_date=start_date,\
                                                                   statistic_type=1,\
                                                                   shop_id=each_demand[0],\
                                                                   goods_id=each_demand[1])\
                                                        .first()
                if exist_statistic_demand:
                    new_statistic_demand=exist_statistic_demand
                else:
                    if_new=True
            else:
                if_new=True
            # 新加一条记录
            if if_new:
                new_statistic_demand=StatisticsDemand(statistic_type=1,\
                                                      statistic_date=each_demand[11],\
                                                      shop_id=each_demand[0],\
                                                      goods_id=each_demand[1],\
                                                      statistic_datetime=each_demand[10],\
                                                      statistic_year=int(each_demand[11].strftime("%Y")),\
                                                      statistic_month=int(each_demand[11].strftime("%m")),\
                                                      statistic_week=int(each_demand[11].strftime("%W")))
                statistic_session.add(new_statistic_demand)
                statistic_session.flush()

            new_statistic_demand.total_order_amount=each_demand[2]
            new_statistic_demand.total_wasted=each_demand[3]
            new_statistic_demand.total_sale=each_demand[4]
            new_statistic_demand.total_arrival=each_demand[5]
            new_statistic_demand.average_purchase_price=average_purchase_price
            new_statistic_demand.average_price=average_price
            new_statistic_demand.total_current_stock=each_demand[8]
            new_statistic_demand.demand_count=demand_count
            new_statistic_demand.statistic_datetime=each_demand[10]
            statistic_session.flush()
        return True


    @classmethod
    def update_by_week_and_month(cls,statistic_session,start_datetime,statistic_type):
        """按周或者月更新统计数据
           statistic_type 2: 按月　３：按周
        """
        StatisticsDemand=models_statistic.StatisticsDemand
        Demand=models.Demand
        start_date= datetime.date(start_datetime.year,start_datetime.month,start_datetime.day)
        group_type=None
        if statistic_type==2:
            group_type=StatisticsDemand.statistic_week
        elif statistic_type==3:
            group_type=StatisticsDemand.statistic_month

        day_statistic_demands=statistic_session.query(StatisticsDemand.shop_id,
                                                      StatisticsDemand.goods_id,\
                                                      func.sum(StatisticsDemand.total_order_amount),\
                                                      func.sum(StatisticsDemand.total_wasted),\
                                                      func.sum(StatisticsDemand.total_sale),func.sum(StatisticsDemand.total_arrival),\
                                                      func.sum(StatisticsDemand.average_purchase_price),func.sum(StatisticsDemand.average_price),\
                                                      func.sum(StatisticsDemand.total_current_stock),func.count(StatisticsDemand.id),\
                                                      func.max(StatisticsDemand.statistic_datetime),StatisticsDemand.statistic_year,\
                                                      StatisticsDemand.statistic_month,StatisticsDemand.statistic_week)\
                                                .order_by(StatisticsDemand.statistic_year,group_type)\
                                                .filter(StatisticsDemand.statistic_date>=start_date)\
                                                .filter_by(statistic_type=statistic_type-1)\
                                                .group_by(StatisticsDemand.shop_id,\
                                                            StatisticsDemand.goods_id,\
                                                            StatisticsDemand.statistic_year,\
                                                            group_type)\
                                                .all()
        if not day_statistic_demands:
            return True
        for each_demand in day_statistic_demands:
            average_purchase_price=0
            average_price=0
            demand_count=each_demand[9]
            if demand_count:
                average_purchase_price=each_demand[6]/demand_count
                average_price=each_demand[7]/demand_count
            new_statistic_demand=None
            if_new=False
            # 统计按周的数据
            if statistic_type==2:
                if each_demand[11]==int(start_date.strftime("%Y")) and each_demand[13]==int(start_date.strftime("%W")):
                    exist_statistic_demand=statistic_session.query(StatisticsDemand)\
                                                            .filter_by(statistic_year=each_demand[11],\
                                                                       statistic_week=each_demand[13],\
                                                                       statistic_type=statistic_type,\
                                                                       shop_id=each_demand.shop_id,\
                                                                       goods_id=each_demand.goods_id)\
                                                            .first()
                    if exist_statistic_demand:
                        new_statistic_demand=exist_statistic_demand
                    else:
                        if_new=True
                else:
                    if_new=True
            # 统计按月的数据
            elif statistic_type==3:
                if each_demand[11]==int(start_date.strftime("%Y")) and each_demand[12]==int(start_date.strftime("%m")):
                    exist_statistic_demand=statistic_session.query(StatisticsDemand)\
                                                            .filter_by(statistic_year=each_demand[11],\
                                                                       statistic_month=each_demand[12],\
                                                                       statistic_type=statistic_type,\
                                                                       shop_id=each_demand.shop_id,\
                                                                       goods_id=each_demand.goods_id)\
                                                            .first()
                    if exist_statistic_demand:
                        new_statistic_demand=exist_statistic_demand
                    else:
                        if_new=True
                else:
                    if_new=True
            if if_new:
                new_statistic_demand=StatisticsDemand(statistic_type=statistic_type,\
                                                      shop_id=each_demand[0],\
                                                      goods_id=each_demand[1],\
                                                      statistic_year=each_demand[11],\
                                                      statistic_month=each_demand[12],\
                                                      statistic_week=each_demand[13])
                statistic_session.add(new_statistic_demand)
                statistic_session.flush()
            new_statistic_demand.total_order_amount=each_demand[2]
            # 重要点，因为数据录入的时候，昨日损耗和昨日销量是保存在今天这条录入记录的，
            # 所以，在进行按周和按月统计的时候，统计的时间需要错开，也就是说损耗统计和
            # 销量统计需要减去统计周期（按周/按月）的起始天的，并加上下个周期起始天的数据

            # 首先重新计算统计日期
            if statistic_type==2:
                new_start_datetime,new_end_datetime=TimeFunc.get_week_start_end(each_demand[10])
            elif statistic_type==3:
                new_start_datetime,new_end_datetime=TimeFunc.get_month_start_end(each_demand[10])
            # 统计起始天昨日消耗和昨日销量
            day_statistic_demand_base=statistic_session.query(StatisticsDemand.total_wasted,\
                                                                  StatisticsDemand.total_sale)\
                                                          .filter_by(shop_id=each_demand[0],\
                                                                      goods_id=each_demand[1])

            start_date_statistic_demand =day_statistic_demand_base.filter_by(statistic_date=new_start_datetime.strftime("%Y-%m-%d"))\
                                                                  .first()
            next_start_date_statistic_demand=day_statistic_demand_base.filter_by(statistic_date=new_end_datetime.strftime("%Y-%m-%d"))\
                                                                      .first()
            decrease_wasted=0
            decrease_sale=0
            increase_wasted=0
            increase_sale=0
            if start_date_statistic_demand:
               decrease_wasted=start_date_statistic_demand[0]
               decrease_sale=start_date_statistic_demand[1]
            if next_start_date_statistic_demand:
               increase_wasted=next_start_date_statistic_demand[0]
               increase_sale=next_start_date_statistic_demand[1]
            # 累计损耗和销量数据修正
            new_statistic_demand.total_wasted=each_demand[3]-decrease_wasted+increase_wasted
            new_statistic_demand.total_sale=each_demand[4]-decrease_sale+increase_sale

            new_statistic_demand.total_arrival=each_demand[5]
            new_statistic_demand.average_purchase_price=average_purchase_price
            new_statistic_demand.average_price=average_price
            new_statistic_demand.total_current_stock=each_demand[8]
            new_statistic_demand.demand_count=demand_count
            new_statistic_demand.statistic_datetime=each_demand[10]
            new_statistic_demand.statistic_date=each_demand[10].strftime("%Y-%m-%d")
            statistic_session.flush()
        return True

    @classmethod
    def demand_statistic(cls,session,statistic_session):
        """统计所有的要货请求，用于后续数据统计使用
        """

        #首先按天统计要货情况
        StatisticsDemand=models_statistic.StatisticsDemand
        Demand=models.Demand
        old_statistic_demand=statistic_session.query(StatisticsDemand)\
                                              .filter_by(statistic_type=1)\
                                              .order_by(StatisticsDemand.statistic_datetime.desc())\
                                              .first()
        start_datetime=None
        if not old_statistic_demand:
            # 如果一条记录都没有，说明此前还没有更新数据，则统计demand的开始时间就是所有demand的最小时间
            early_demand=session.query(Demand)\
                                .order_by(Demand.create_date)\
                                .first()
            start_datetime=early_demand.create_date
        else:
            #　这里注意要增加１秒　免得会重复统计已经统计过的，那么为啥不在query语句中使用大于呢，这是为了满足在old_statistic_demand=None的时候
            start_datetime=old_statistic_demand.statistic_datetime+datetime.timedelta(seconds=1)
        cls.update_by_day(session,statistic_session,start_datetime)
        statistic_session.flush()

        #其次统计按周的要货情况
        old_statistic_demand=statistic_session.query(StatisticsDemand)\
                                              .filter_by(statistic_type=2)\
                                              .order_by(StatisticsDemand.statistic_datetime.desc())\
                                              .first()
        start_datetime=None
        if not old_statistic_demand:
            # 如果一条记录都没有，说明此前还没有按周的更新数据，则统计的开始时间就是所有按天统计的最小时间
            early_demand=statistic_session.query(StatisticsDemand)\
                                          .filter_by(statistic_type=1)\
                                          .order_by(StatisticsDemand.statistic_datetime)\
                                          .first()
            # 还没有任何按天统计的要货记录
            if not early_demand:
                return True
            start_datetime=early_demand.statistic_datetime
        else:
            start_datetime=old_statistic_demand.statistic_datetime
        week_start_datetime,week_end_datetime=TimeFunc.get_week_start_end(start_datetime)
        cls.update_by_week_and_month(statistic_session,week_start_datetime,2)
        statistic_session.flush()

        #最后统计按月的要货情况
        old_statistic_demand=statistic_session.query(StatisticsDemand)\
                                              .filter_by(statistic_type=3)\
                                              .order_by(StatisticsDemand.statistic_date.desc())\
                                              .first()
        start_datetime=None
        if not old_statistic_demand:
            # 如果一条记录都没有，说明此前还没有按月的更新数据，则统计的开始时间就是所有按周统计的最小时间
            early_demand=statistic_session.query(StatisticsDemand)\
                                          .filter_by(statistic_type=2)\
                                          .order_by(StatisticsDemand.statistic_date)\
                                          .first()
            # 还没有任何按周统计的要货记录
            if not early_demand:
                return True
            start_datetime=early_demand.statistic_date
        else:
            start_datetime=old_statistic_demand.statistic_date
        month_start_datetime,month_end_datetime=TimeFunc.get_month_start_end(start_datetime)
        cls.update_by_week_and_month(statistic_session,month_start_datetime,3)
        statistic_session.commit()
        return True