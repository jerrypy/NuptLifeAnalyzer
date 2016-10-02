#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urlparse import urlparse
from datetime import date
import datetime
import json
from requests import Session

import gevent
from config import Config
from app_config import Config as APP_CONFIG
from NUPTCrawlerBase import NUPTCrawlerBase
from lib.util import api
from lib.http import req
from lib.PageParser import EhomeParser


class EhomeCrawler(NUPTCrawlerBase):
    def __init__(self, db=None, debug=False):
        super(EhomeCrawler, self).__init__(debug=debug)
        self.URLS = Config.EHOME_URLS
        self.host = urlparse(self.URLS['COOKIE']).netloc
        self.proxies = Config.PROXIES
        self.session = Session()
        self.session.proxies = self.proxies
        self.cookies = None
        self.iplanet = None
        self.student_id = ''
        self.cardno = None
        self.collection = db.ehome

    def _login(self, login_data):
        resp = req(self.URLS['COOKIE'], 'get', host=self.host)
        if resp is None:
            return Config.SERVER_MSG['SERVER_ERROR']
        api.logger.info('[+] ID: %s got ehome cookies.' % login_data['student_id'])

        self.cookies = resp.cookies
        self.student_id = login_data['student_id']
        payload = {
            'email': login_data['student_id'],
            'password': login_data['password']
        }

        resp = req(self.URLS['LOGIN'], 'post', data=payload, cookies=self.cookies)
        if resp is None:
            return Config.SERVER_MSG['SERVER_ERROR']
        # 校园系统bug 无需这一步
        if resp.url != self.URLS['LOGIN_SUCCESS']:
            return Config.SERVER_MSG['WRONG_PASSWORD']

        api.logger.info('[+] ID: %s login ehome.' % login_data['student_id'])
        self.iplanet = resp.history[0].cookies
        self.session.cookies = self.iplanet
        return Config.SERVER_MSG['LOGIN_SUCCESS']

    def login(self, login_data=None):
        return self._login(login_data=login_data)

    def _get_cardno(self):
        info = []
        resp = self.session.get(self.URLS['INDEX'])
        if resp is None:
            return info
        content = resp.text
        info = EhomeParser.parse_ehome_info(content)
        api.logger.info('[+] got cardno: %s.' % info['usercode'])

        # 写至数据库
        self.insert_to_db('info', info)

        return info

    def _get_loss(self, start_date, cardno):
        rec = []
        data = {
            'param_0': 0,
            'param_1': 100
        }

        params = {
            'className': 'cn.com.system.query.DealQuery',
            'methodName': 'getDealRegisterLoss',
            'paramCount': '5',
            'param_2': start_date,
            'param_3': str(date.today()),
            'param_4': cardno
        }

        resp = self.session.post(self.URLS['REC'], params=params, data=data)
        if resp is None:
            return None
        rec = resp.json()['results']
        rec = dict(loss_rec=rec)
        self.insert_to_db('loss_rec', rec)

        return rec # list of dicts

    def _get_rec(self, start_date, cardno):
        rec = []

        # 这里查的是最后的数据统计信息，不是原始信息。
        # res = self.find_in_db('rec')
        # if res is not None and not res['rec']['incomplete']:
        #     return res

        # 获取用户校园卡号，图书馆信息处也可以查询
        info = self._get_cardno()
        usercode = info.get('usercode')
        if not usercode:
            return rec

        fanka_data = {
            'param_0': 0,
            'param_1': 1  # 每页显示数
        }

        params = {
            'className': 'cn.com.system.query.DealQuery',
            'methodName': 'getDealQuery',
            'paramCount': '6',
            'param_2': start_date,
            'param_3': str(date.today()),
            'param_4': '-1',
            'param_5': cardno
        }

        #: 第一次请求，只返回1条结果 fanka_data param_1=1
        #: 目的是获取到总数
        #: 再发送第二条数据，获取全部结果，但是服务器最多一次只返回1024条数据。
        resp = self.session.post(self.URLS['REC'], params=params, data=fanka_data)
        if resp is None:
            return None
        res = resp.json()
        total_count = int(res['totalCount'])

        api.logger.info('[+] got total_count %s of %s' % (total_count, cardno))
        if total_count > 0:
            threads = []
            for i in range(0, total_count, 1024):
                post_data = dict(param_0=i,
                                 param_1=1024)
                threads.append(gevent.spawn(self.session.post, self.URLS['REC'], params=params, data=post_data))

            gevent.joinall(threads)
            for t in threads:
                if t.value is not None:
                    rec.extend(t.value.json()['results'])
        else:
            pass





        # if total_count > 0:
        #     fanka_data['param_1'] = total_count
        #     resp = self.session.post(self.URLS['REC'], params=params, data=fanka_data)
        #     if resp is None:
        #         return "[]"
        #     res = resp.json()
        #     rec = res['results']
        # else:
        #     pass

        rec = dict(items=rec)
        self.insert_to_db('rec', rec)

        return rec

    def get_data(self, start_date, cardno):
        """

        :param start_date: 应从正方入学日期获取
        :return:
        """
        self.cardno = cardno
        api.logger.info('[+] start fetching ehome data for %s' % self.cardno)

        # 这里查的是最后的数据统计信息，不是原始信息。
        res = self.find_in_db('analysis')
        if res is not None and not res['analysis']['incomplete']:
            if (datetime.datetime.now() - self.find_in_db('fetch_date')['fetch_date']).days > APP_CONFIG.EHOME_DATA_TTL:
                pass
            else:
                return res

        threads = [
            gevent.spawn(self._get_rec, start_date, cardno),
            gevent.spawn(self._get_loss, start_date, cardno)
        ]
        gevent.joinall(threads)

        res = dict(loss_rec=threads[1].value,
                   rec=threads[0].value)

        # 进行分析处理后，写至数据库分析字段。
        analysis = self.analyze(res)
        self.insert_to_db('analysis', analysis, date=True)

        return {'analysis': analysis}

    def analyze(self, res):
        api.logger.info('[*] start analyzing %s card data...' % self.cardno)

        if res['rec'] is None or res['rec']['items'] == []:
            return None

        recs = res['rec']['items']
        total_consume = 0.0 # 总消费
        highest_consume = dict(window='',
                               money=0,
                               date='') # 单次最高消费
        highest_month_consume = dict(money=0,
                                     month='') # 最高单月消费
        first_consume = dict(window='',
                             money=0,
                             date='2099-01-01 00:00:00') # 第一次消费
        highest_left = dict(money=0.0,
                            date='') # 最高余额
        lowest_left = dict(money=99999999,
                           date='') # 最低余额
        favor_window = dict(name='',
                            times=0,
                            money=0) # 最喜欢的窗口
        bank_charge = dict(times=0,
                           money=0) # 银行圈存
        bath_charge = dict(times=0,
                           money=0) # 控水转账
        elec_charge = dict(times=0,
                           money=0) # 电费
        net_charge = dict(times=0,
                          money=0) # 城市热点

        windows = dict()
        month_consume = dict() # 单月消费

        for i in recs:
            # 总消费
            if i['CONTYPE'] != u'2' and i['CONTYPE'] != u'19' and i['CONTYPE'] != u'13':
                total_consume += float(i['TRANSACTMONEY'])


                # 单月最高消费
                if i['DISPOSETIME'][0:7] in month_consume:
                    month_consume[i['DISPOSETIME'][0:7]]['money'] += float(i['TRANSACTMONEY'])
                else:
                    month_consume[i['DISPOSETIME'][0:7]] = dict(money=float(i['TRANSACTMONEY']))
                if month_consume[i['DISPOSETIME'][0:7]]['money'] > highest_month_consume['money']:
                    highest_month_consume = dict(money=month_consume[i['DISPOSETIME'][0:7]]['money'],
                                           month=i['DISPOSETIME'][0:7])

            # 最高余额
            if float(i['CURRENTDBMONEY']) > highest_left['money']:
                highest_left = dict(money=float(i['CURRENTDBMONEY']),
                                    date=i['DISPOSETIME'])

            # 最低余额
            if float(i['CURRENTDBMONEY']) < lowest_left['money']:
                lowest_left = dict(money=float(i['CURRENTDBMONEY']),
                                   date=i['DISPOSETIME'])


            if i['CONTYPE'] == u'0':
                # 第一次消费
                if i['DISPOSETIME'] < first_consume['date']:
                    first_consume = dict(window=i['WINNAME'],
                                         money=i['TRANSACTMONEY'],
                                         date=i['DISPOSETIME'])

                # 最高单次消费
                if float(i['TRANSACTMONEY']) > highest_consume['money']:
                    highest_consume = dict(window=i['WINNAME'],
                                           money=float(i['TRANSACTMONEY']),
                                           date=i['DISPOSETIME'])

                # 最多次消费窗口
                if i['WINNAME'] in windows:
                    windows[i['WINNAME']]['times'] += 1
                    windows[i['WINNAME']]['money'] += float(i['TRANSACTMONEY'])
                else:
                    windows[i['WINNAME']] = dict(times = 1,
                                                 money=float(i['TRANSACTMONEY']))
                if windows[i['WINNAME']]['times'] > favor_window['times']:
                    favor_window = dict(name=i['WINNAME'],
                                        times=windows[i['WINNAME']]['times'],
                                        money=windows[i['WINNAME']]['money'])

            # 银行圈存
            elif i['CONTYPE'] == u'13' or i['CONTYPE'] == u'2':
                bank_charge['money'] += float(i['TRANSACTMONEY'])
                bank_charge['times'] += 1

            # 电控转账
            elif i['CONTYPE'] == u'4':
                elec_charge['money'] += float(i['TRANSACTMONEY'])
                elec_charge['times'] += 1

            # 城市热点和机房转账
            elif i['CONTYPE'] == u'25' or i['CONTYPE'] == u'24':
                net_charge['money'] += float(i['TRANSACTMONEY'])
                net_charge['times'] += 1

            # 充水
            elif i['CONTYPE'] == u'26':
                bath_charge['money'] += float(i['TRANSACTMONEY'])
                bath_charge['times'] += 1

            else:
                pass


        return dict(total_consume=total_consume,
                    first_consume=first_consume,
                    highest_consume=highest_consume,
                    highest_month_consume=highest_month_consume,
                    highest_left=highest_left,
                    lowest_left=lowest_left,
                    favor_window=favor_window,
                    bank_charge=bank_charge,
                    elec_charge=elec_charge,
                    bath_charge=bath_charge,
                    net_charge=net_charge)


if __name__ == '__main__':
    # print str(date.today())
    from app_config import Config as APP_CONFIG
    from pymongo import MongoClient

    conn = MongoClient(APP_CONFIG.MONGO_URI)
    db = conn.youji
    db.authenticate(APP_CONFIG.MONGO_USER, APP_CONFIG.MONGO_PWD)
    ec = EhomeCrawler(db=db, debug=True)
    ec._login(login_data={'student_id': '', 'password': ''})
    print ec.get_data('2012-09-01', "")
