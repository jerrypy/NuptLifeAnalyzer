#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
celery任务定义。
"""

import datetime
from pymongo import MongoClient
from celery import Task
from celery.utils.log import get_task_logger
from celery.contrib import rdb

from app import celery
# from decorators import unpack_cookies
# from NuptCrawlers.ZfCrawler import ZfCrawler
from NuptCrawlers.ZfCrawlerDecaptcha import ZfCrawlerDecaptcha
from NuptCrawlers.LibCrawler import LibCrawler
from NuptCrawlers.EhomeCrawler import EhomeCrawler
from app_config import Config as APP_CONFIG
from NuptCrawlers.config import Config as CRAWLER_CONFIG
from NuptCrawlers.lib.http import CODE

logger = get_task_logger(__name__)
SERVER_MSG = CRAWLER_CONFIG.SERVER_MSG

#: 整个worker生命周期，正方爬虫共用一套代码。
#: 原因见ZfCrawler docstring
# zc = ZfCrawler()
# 20160717 通过第三方平台识别验证码，所以正方爬虫对象不再需要公用


class CrawlerTask(Task):
    abstract = True
    _db = None

    @property
    def db(self):
        """
        reduce db connections
        Reference: http://docs.celeryproject.org/en/latest/userguide/tasks.html#instantiation
        :return:
        """
        if self._db is None:
            conn = MongoClient(APP_CONFIG.MONGO_URI)
            db = getattr(conn, APP_CONFIG.MONGO_DB_NAME)
            db.authenticate(APP_CONFIG.MONGO_USER, APP_CONFIG.MONGO_PWD)
            self._db = db
        return self._db


# @celery.task
# @unpack_cookies
# def zf_login(login_data, cookies=None):
#     # rdb.set_trace()
#     login_res = zc.login(login_data, cookies)
#     return {'code': login_res[1], 'student_id': login_res[0]}
#
#
# @celery.task(bind=True, base=CrawlerTask)
# @unpack_cookies
# def zf_crawler(self, student_id, cookies=None):
#     info = zc.get_personal_info(cookies, student_id, self.db)
#     if info != SERVER_MSG['SERVER_ERROR']:
#         self.update_state(state='INFO_GOT',
#                           meta={'zf_info': info})
#     else:
#         return CODE.SERVER_ERROR
#     data = zc.get_data(cookies, student_id)
#     return {'zf_info': info, 'data': data}


@celery.task(bind=True, base=CrawlerTask)
def zf_crawler_decaptcha(self, login_data):
    """正方爬虫任务"""

    #-----------------查询黑名单逻辑开始---------------------------#
    try:
        # 查询是否在黑名单中
        # rdb.set_trace()
        bl = self.db.blacklist.find_one({'student_id': login_data['student_id']},
                                       {'_id': 0})
        if bl is not None:
            import datetime
            if datetime.datetime.now() >= bl['ban_date'] + datetime.timedelta(bl['ban_days']):
                # 已经过了BAN的日期，从数据库中移除
                self.db.blacklist.remove({'student_id': login_data['student_id']})
            else:
                # 还在BAN日期内
                r = CODE.SHAME_ON_YOU
                r['msg'] = (bl['ban_date'] + datetime.timedelta(bl['ban_days'])).strftime('%Y年%m月%d日 %H时%M分%S秒')
                return r
        else:
            pass
    except Exception:
        return CODE.SERVER_ERROR
    #-----------------查询黑名单逻辑结束---------------------------#

    zcd = ZfCrawlerDecaptcha(db=self.db)
    login_res = zcd.login(login_data)
    if login_res[1] == SERVER_MSG['LOGIN_SUCCESS']:
        # 登录成功
        self.update_state(state='LOGIN_SUCCESS',
                          meta={'login_res': login_res})
    else:
        # 登录失败，返回状态
        return {'code': login_res[1], 'student_id': login_res[0]}

    info = zcd.get_personal_info(login_data['student_id'])
    if info != SERVER_MSG['SERVER_ERROR']:

        # 入学时间小于6个月的返回
        import datetime
        now = datetime.datetime.now()
        e = datetime.datetime.strptime(info['entrance_date'], '%Y-%m-%d')
        delta = (now - e).days
        if delta < 6 * 30:
            return CODE.TOO_YOUNG

        self.update_state(state='INFO_GOT',
                          meta={'zf_info': info})
    else:
        return CODE.SERVER_ERROR

    data = zcd.get_data(login_data['student_id'])
    if data is None:
        return CODE.SERVER_ERROR

    d = info['entrance_date'].split('-')
    entrance_date = str(d[0]) + u'年' + str(d[1]) + u'月' + str(d[2]) + u'日'
    weather = self.db.nj_weather.find_one({'date': entrance_date},
                                            {'_id': 0})

    data['weather'] = weather
    return {'zf_info': info, 'data': data}


@celery.task(bind=True, base=CrawlerTask)
def lib_crawler(self, login_data):
    """图书馆爬虫任务"""
    lc = LibCrawler(db=self.db)
    login_res = lc.login(login_data)
    if login_res == SERVER_MSG['LOGIN_SUCCESS']:
        self.update_state(state='LOGIN_SUCCESS',
                          meta={})
    else:
        return {'login_res': login_res}
    data = lc.get_data()
    if data is None:
        return CODE.SERVER_ERROR
    return {'data': data}


@celery.task(bind=True, base=CrawlerTask)
def ehome_crawler(self, login_data, start_date, cardno):
    ec = EhomeCrawler(db=self.db)
    login_res = ec.login(login_data)
    if login_res == SERVER_MSG['LOGIN_SUCCESS']:
        self.update_state(state='LOGIN_SUCCESS',
                          meta={})
    else:
        return {'login_res': login_res}
    data = ec.get_data(start_date, cardno)
    if data is None:
        return CODE.SERVER_ERROR
    return {'data': data}


@celery.task(bind=True, base=CrawlerTask)
def try_youji(self):
    """游客任务"""
    # TODO 数据库操作错误处理
    try:
        zf_data = self.db.zf.find_one({'student_id': 'B13041317'},
                                      {'_id': 0, 'info': 1, 'analysis': 1})
        lib_data = self.db.lib.find_one({'student_id': 'B13041317'},
                                        {'_id': 0, 'analysis': 1})
        d = zf_data['info']['entrance_date'].split('-')
        entrance_date = str(d[0]) + u'年' + str(d[1]) + u'月' + str(d[2]) + u'日'
        weather = self.db.nj_weather.find_one({'date': entrance_date},
                                              {'_id': 0})
        # ehome_data = self.db.ehome.find_one({'student_id': APP_CONFIG.ADMIN_STUDENT_ID},
        #                                     {'_id': 0, 'analysis': 1})
        zf_data['weather'] = weather
    except Exception:
        return None


    return {'zf_data': zf_data,
            'lib_data': lib_data,
            }
            # 'ehome_data': ehome_data}

@celery.task(bind=True, track_started=False)
def debug(self):
    print('Request: {0!r}'.format(self.request))
