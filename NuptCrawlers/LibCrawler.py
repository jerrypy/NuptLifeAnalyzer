#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PIL import Image
import pytesseract
from StringIO import StringIO
import json
import gevent
import datetime

from config import Config
from app_config import Config as APP_CONFIG
from NUPTCrawlerBase import NUPTCrawlerBase
from lib.util import api
from lib.http import req
from lib.PageParser import LibParser


class LibCrawler(NUPTCrawlerBase):
    """图书馆系统个爬虫"""
    def __init__(self, db=None, debug=False):
        super(LibCrawler, self).__init__(debug=debug)
        self.debug = debug
        self.URLS = Config.LIB_URLS
        self.cookies = None
        self.student_id = ''
        self.collection = db.lib

    def _get_captcha(self, crack=True):
        resp = req(self.URLS['CAPTCHA'], 'get')
        self.cookies = resp.cookies
        i = Image.open(StringIO(resp.content))
        if self.debug:
            i.save('lib_captcha.png')
        if crack:
            guess = pytesseract.image_to_string(i)
            # i.close()
            return guess
        else:
            return resp.content

    def _login(self, login_data=None):
        self.student_id = student_id = login_data['student_id']
        login_data = {
            'number': login_data['student_id'],
            'passwd': login_data['password'],
            'captcha': self._get_captcha(),
            'select': 'cert_no',
            'returnUrl': ''
        }
        resp = req(self.URLS['LOGIN'], 'post', data=login_data, cookies=self.cookies)
        if resp is None:
            return Config.SERVER_MSG['SERVER_ERROR']
        if resp.url == self.URLS['LOGIN_SUCCESS']:
            self.student_id = login_data['number']
            api.logger.info('[+] ID: %s login lib successfully.' % self.student_id)
            return Config.SERVER_MSG['LOGIN_SUCCESS']
        elif self.URLS['WRONG_PASS_FINGER'].encode('utf8') in resp.content:
            api.logger.warning('[+] ID: %s login lib failed.' % self.student_id)
            return Config.SERVER_MSG['WRONG_PASSWORD']
        elif self.URLS['WRONG_CAPTCHA_FINGER'] in resp.content:
            # TODO 验证码错误，重试
            api.logger.critical('[+] ID: %s crack captcha failed.' % self.student_id)
            return Config.SERVER_MSG['WRONG_CAPTCHA']
        else:
            api.logger.error('[-] unknown error.')
            return Config.SERVER_MSG['SERVER_ERROR']

    def login(self, login_data=None):
        return self._login(login_data=login_data)

    def _get_info(self):
        """
        获取用户信息
        """
        res = []
        resp = req(self.URLS['INFO'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_info(content)
        api.logger.info('[+] ID: %s got lib info.' % self.student_id)

        # TODO 做好数据库操作的异常处理
        # 写至数据库
        self.insert_to_db('info', res)

        return res

    def _get_current_list(self):
        """
        获取当前借阅信息
        """
        res = []
        resp = req(self.URLS['CURRENT'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_curlst(content)
        api.logger.info('[+] ID: %s got lib current list.' % self.student_id)

        # 写至数据库
        self.insert_to_db('current_list', res)

        return res

    def _get_history(self):
        """
        获取借阅历史
        """
        res = []
        data = {
            'para_string': 'all',
            'topage': 1
        }
        resp = req(self.URLS['HISTORY'], 'post', data=data, cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_common(content, tr_start=1, td_start=1)
        api.logger.info('[+] ID: %s got lib history.' % self.student_id)

        # 写至数据库
        self.insert_to_db('history', res)

        return res

    def _get_recommend(self):
        """
        获取荐购信息
        """
        res = []
        resp = req(self.URLS['RECOMMEND'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_common(content, tr_start=1)
        api.logger.info('[+] ID: %s got lib recommend.' % self.student_id)

        # 写至数据库
        self.insert_to_db('recommend', res)

        return res

    def _get_reserve(self):
        """
        获取预约信息
        """
        res = []
        resp = req(self.URLS['RESERVE'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_common(content, tr_start=1)
        api.logger.info('[+] ID: %s got lib reserve.' % self.student_id)

        # 写至数据库
        self.insert_to_db('reserve', res)

        return res

    def _get_book_shelf(self):
        """
        获取书架
        """
        res = []
        resp = req(self.URLS['BOOKSHELF'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_shelf(content)
        api.logger.info('[+] ID: %s got lib book shelf.' % self.student_id)

        # 写至数据库
        self.insert_to_db('book_shelf', res)

        return res

    def _get_payment(self):
        """
        获取罚款信息
        """
        res = []
        resp = req(self.URLS['FINE'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_common(content, tr_start=1, tr_end=-1)
        api.logger.info('[+] ID: %s got lib payment.' % self.student_id)

        # 写至数据库
        self.insert_to_db('payment', res)

        return res

    def _get_payment_detail(self):
        """
        获取罚款条目
        """
        res = []
        resp = req(self.URLS['FINE_DETAIL'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_common(content, tr_start=1)
        api.logger.info('[+] ID: %s got lib payment details.' % self.student_id)

        # 写至数据库
        self.insert_to_db('payment_detail', res)

        return res

    def _get_comment(self):
        """
        获取书评
        """
        res = []
        resp = req(self.URLS['COMMENT'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_comment(content)
        api.logger.info('[+] ID: %s got lib comment.' % self.student_id)

        # 写至数据库
        self.insert_to_db('comment', res)

        return res

    def _get_search(self):
        """
        获取检索历史
        """
        res = []
        resp = req(self.URLS['SEARCH'], 'get', cookies=self.cookies)
        if resp is None:
            return res
        content = resp.content
        res = LibParser.parse_lib_search(content)
        api.logger.info('[+] ID: %s got lib search record.' % self.student_id)

        # 写至数据库
        self.insert_to_db('search', res)

        return res

    def get_data(self):
        api.logger.info('[+] start fetching ID:%s data.' % self.student_id)

        # 这里查的是最后的数据统计信息，不是原始信息。
        res = self.find_in_db('analysis')
        if res is not None and not res['analysis']['incomplete']:
            if (datetime.datetime.now() - self.find_in_db('fetch_date')['fetch_date']).days > APP_CONFIG.LIB_DATA_TTL:
                pass
            else:
                return res

        threads = [
            gevent.spawn(self._get_info),
            gevent.spawn(self._get_current_list),
            gevent.spawn(self._get_comment),
            gevent.spawn(self._get_search),
            gevent.spawn(self._get_payment),
            gevent.spawn(self._get_payment_detail),
            gevent.spawn(self._get_recommend),
            gevent.spawn(self._get_book_shelf),
            gevent.spawn(self._get_reserve),
            gevent.spawn(self._get_history)
        ]

        gevent.joinall(threads)

        res = dict(info=threads[0].value,
                   current_list=threads[1].value,
                   comment=threads[2].value,
                   search=threads[3].value,
                   payment=threads[4].value,
                   payment_detail=threads[5].value,
                   recommend=threads[6].value,
                   book_shelf=threads[7].value,
                   reserve=threads[8].value,
                   history=threads[9].value)

        # 进行分析处理后，写至数据库分析字段。
        analysis = self.analyze(res)
        self.insert_to_db('analysis', analysis, date=True)

        return {'analysis': analysis}

    def analyze(self, res):
        if res['history'] == [] or res['payment_detail'] == [] or res['comment'] == [] \
                or res['history'] is None or res['payment_detail'] is None or res['comment'] is None:
            return None
        def days_sum(borrow_date, return_date):
            """
            计算借书时间
            :param borrow_date: 借书日期
            :param return_date: 归还日期
            :return:
            """
            borrow_date = datetime.datetime.strptime(borrow_date, '%Y-%m-%d')
            return_date = datetime.datetime.strptime(return_date, '%Y-%m-%d')
            delta = return_date - borrow_date
            return delta.days

        history = res['history']['items']
        # 获取借的第一本书
        if len(history) > 0:
            first_borrow_book = history[-1]
        else:
            first_borrow_book = False # 没借过书，提醒去借一本

        if first_borrow_book:
            # 获取借的次数最多的书
            borrow_frequency = dict()
            for book in history:
                if book[1] in borrow_frequency.keys():
                    borrow_frequency[book[1]]['times'] += 1
                    borrow_frequency[book[1]]['days'] += days_sum(book[3], book[4])
                else:
                    borrow_frequency[book[1]] = dict(times=1, days=days_sum(book[3], book[4]))


            most_borrow_book = dict(name='', times=0, days=0)
            for book in borrow_frequency:
                if borrow_frequency[book]['times'] > most_borrow_book['times']:
                    # 次数占权重大
                    most_borrow_book = dict(name=book,
                                            times=borrow_frequency[book]['times'],
                                            days=borrow_frequency[book]['days'])
                elif borrow_frequency[book]['times'] == most_borrow_book['times']:
                    # 如果次数相同，算借的时间
                    if borrow_frequency[book]['days'] > most_borrow_book['days']:
                        most_borrow_book = dict(name=book,
                                                times=borrow_frequency[book]['times'],
                                                days=borrow_frequency[book]['days'])
                else:
                    continue

        # 获取罚款最多的书
        book_payment = dict()
        for book in res['payment_detail']['items']:
            if book[2] in book_payment.keys():
                book_payment[book[2]] += float(book[7])
            else:
                book_payment[book[2]] = float(book[7])

        most_fine_book = dict(name='', payment=0)
        for book in book_payment:
            if book_payment[book] > most_fine_book['payment']:
                most_fine_book = dict(name=book,
                                      payment=book_payment[book])

        # 获取图书评论
        if len(res['comment']['items']) > 0:
            first_comment = res['comment']['items'][-1]
        else:
            # 没有的话提醒去留一条
            first_comment = False


        res = dict(first_borrow_book=first_borrow_book,
                   first_comment=first_comment
                   )
        if first_borrow_book:
            res['first_borrow_book_days']=days_sum(first_borrow_book[3], first_borrow_book[4])
            res['most_fine_book'] = most_fine_book
            res['most_borrow_book']=most_borrow_book

        return res

if __name__ == '__main__':
    from pymongo import MongoClient
    from app_config import Config as APP_CONFIG
    conn = MongoClient(APP_CONFIG.MONGO_URI)
    db = conn.youji
    db.authenticate(APP_CONFIG.MONGO_USER, APP_CONFIG.MONGO_PWD)
    lc = LibCrawler(db=db, debug=True)
    login_data = {
        'student_id': '',
        'password': ''
    }
    print lc.login(login_data)
    print lc.get_data()