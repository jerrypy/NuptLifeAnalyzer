#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime


class NUPTCrawlerBase(object):
    """
    NUPT爬虫通用类
    """
    def __init__(self, debug=False):
        self.debug = debug

    def _login(self, login_data=None, cookies=None):
        pass

    def login(self, login_data=None, cookies=None):
        return self._login(login_data=login_data, cookies=cookies)

    def get_data(self, cookies=None, student_id=None):
        pass

    def find_in_db(self, key_name):
        res = self.collection.find_one({'student_id': self.student_id}, {'_id': 0, key_name: 1})
        if not res:
            return None
        return res

    def insert_to_db(self, key_name, res, date=False):
        """

        :param key_name: 字段名
        :param res: 字段内容
        :param date: 是否需要插入爬取时间
        :return: bool 成功与否
        """
        # TODO 原数据库中有的字段有值，而现在查询没有的，保留原有字段值。 -- 太复杂
        # FIXME incomplete 机制 怎么样做才最好？
        if res is None:
            return False
        res['incomplete'] = False

        add_field = {key_name: res}
        if date:
            add_field['fetch_date'] = datetime.datetime.now()
        return \
            self.collection.update_one({"student_id": self.student_id},
                                       {'$set': add_field},
                                       upsert=True) == 1

    def analyze(self, res):
        pass
