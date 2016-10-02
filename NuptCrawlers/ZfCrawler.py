#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from PIL import Image
from StringIO import StringIO
from urlparse import urlparse
import json
import gevent
from celery.contrib import rdb

from config import Config
from NUPTCrawlerBase import NUPTCrawlerBase
from lib.util import api, save_to_qiniu
from lib.http import req
from lib.PageParser import ZfParser


class ZfCrawler(NUPTCrawlerBase):
    """
    cookie是抓取验证码时候的cookie。

    每一个入口，都需要传入cookies和student_id，因为我们需要先展示
    验证码给用户，让用户自行输入，所以这样设计。
    能自动识别验证码后，可以与Lib和Ehome相同的设计。
    """

    def __init__(self, debug=False):
        super(ZfCrawler, self).__init__(debug=debug)
        self.ZF_URLS = Config.ZF_URLS
        self.host = urlparse(self.ZF_URLS['LOGIN']).netloc
        self.vs_regex = r'<input type="hidden" name="__VIEWSTATE" value="((.[^\s])*)" />'
        self.db = None
        self.collection = None

    @staticmethod
    def get_captcha(url=Config.ZF_URLS['CAPTCHA'], debug=False):
        """
        验证码暂时需要用户输入
        模拟教务处验证码获取 http://jwxt.njupt.edu.cn/CheckCode.aspx
        <img src="http://jwxt.njupt.edu.cn/CheckCode.aspx">

        TODO:
            1. 识别验证码， 参考：http://blog.rijnx.com/post/ZF-Checkcode-Verify

        :return: captcha图片流, 正方登录cookie
        :param: url
        :param: debug
        """
        resp = req(url, 'get')
        if resp is None:
            return Config.SERVER_MSG['SERVER_ERROR'], None
        if debug:
            # debug模式下，保存图片到本地查看
            i = Image.open(StringIO(resp.content))
            i.save('test.gif')
        return resp.content, resp.cookies

    def decaptcha(self):
        captcha = req(Config.ZF_URLS['CAPTCHA'], 'get')
        if captcha is None:
            return Config.SERVER_MSG['SERVER_ERROR'], None
        captcha = captcha.content

        data = {
            'file': captcha
        }

        text = req(Config.DECAPTCHA_URL, 'post', files=data).text
        return text

    def _get_viewstate(self, url, cookies=None):
        """
        获取表单viewstate
        """
        resp = req(url, 'get', referer=self.ZF_URLS['LOGIN'], cookies=cookies)
        if resp is None:
            return Config.SERVER_MSG['SERVER_ERROR']
        res = re.search(self.vs_regex, resp.text, re.S)
        if res is None:
            return Config.SERVER_MSG['SERVER_ERROR']
        viewstate = res.group(1)
        return viewstate

    def _login(self, login_data=None, cookies=None):
        """
        登录正方
        :param login_data:
        :param cookies:
        :return: (student_id, 登录结果)
        """
        viewstate = self._get_viewstate(self.ZF_URLS['LOGIN'])
        if viewstate == Config.SERVER_MSG['SERVER_ERROR']:
            return Config.SERVER_MSG['SERVER_ERROR']
        student_id = login_data['student_id']
        login_data = {
            '__VIEWSTATE': viewstate,
            'txtUserName': student_id,
            'TextBox2': Config.TEST_ZF_PASSWORD if student_id == Config.TEST_STUDENT_ID else login_data['zf_password'],
            'txtSecretCode': login_data['zf_captcha'],
            'RadioButtonList1': '学生',
            'Button1': '登录',
            'lbLanguange': '',
            'hidPdrs': '',
            'hidsc': ''
        }
        resp = req(self.ZF_URLS['LOGIN'], 'post', referer=self.ZF_URLS['LOGIN'], data=login_data, cookies=cookies)
        if resp is None:
            return '', Config.SERVER_MSG['SERVER_ERROR']
        if resp.url.startswith(self.ZF_URLS['LOGIN_SUCCESS']):
            api.logger.info('[+] ID: %s login zf successfully.' % (login_data['txtUserName']))
            msg = Config.SERVER_MSG['LOGIN_SUCCESS']
        elif self.ZF_URLS['WRONG_CAPTCHA_FINGER'] in resp.text:
            msg = Config.SERVER_MSG['WRONG_CAPTCHA']
        elif self.ZF_URLS['INVALID_CAPTCHA_FINGER'] in resp.text:
            msg = Config.SERVER_MSG['INVALID_USERNAME']
        elif self.ZF_URLS['WRONG_PASS_FINGER'] in resp.text:
            api.logger.warning('[-] ID: %s login zf failed.' % (login_data['txtUserName']))
            msg = Config.SERVER_MSG['WRONG_PASSWORD']
        elif self.ZF_URLS['COMMENT'] in resp.text:
            api.logger.warning('[-] need to comment for classes.')
            msg = Config.SERVER_MSG['COMMENT_TIME']
        else:
            msg = Config.SERVER_MSG['SERVER_ERROR']
        return login_data['txtUserName'], msg

    def get_personal_info(self, cookies, student_id, db):
        """
        获取个人信息
        """
        # rdb.set_trace()
        if self.collection is None:
            self.collection = getattr(db, 'zf')
        # 先找数据库
        res = self.find_in_db('info', student_id=student_id)
        # 如果数据库中没有记录，或者记录是不完整的，才尝试查询
        if res is not None and not res['info']['incomplete']:
            res = dict(id_num=res['id_num'][-6:], entrance_date=res['entrance_date'])
            return json.dumps(res, ensure_ascii=False)

        url = ZfParser.get_zf_urls(self.ZF_URLS['INFO'], student_id)
        resp = req(url, 'get', referer=self.ZF_URLS['LOGIN'], cookies=cookies)
        if resp is None:
            api.logger.warning('[-] got %s personal info failed.' % student_id)
            return Config.SERVER_MSG['SERVER_ERROR']
        content = resp.text
        res = ZfParser.parse_zf_info(content)
        api.logger.info('[+] got %s personal info successfully.' % student_id)

        # 写至数据库
        self.insert_to_db('info', student_id, res)

        #: 结果不需要全部返回给前段，只需返回必要的字段即可
        #: 身份证后六位，作为登录图书馆默认密码
        #: 入学日期，作为智慧校园查询起始日期
        res = dict(id_num=res['id_num'][-6:], entrance_date=res['entrance_date'])

        return json.dumps(res, ensure_ascii=False)

    def _get_score(self, cookies, student_id):
        """
        获取成绩信息
        """
        url = ZfParser.get_zf_urls(self.ZF_URLS['SCORE'], student_id)
        viewstate = self._get_viewstate(url, cookies=cookies)
        score_data = {
            '__VIEWSTATE': viewstate,
            'ddlXN': '',
            'ddlXQ': '',
            'Button2': '在校学习成绩查询'
        }
        resp = req(url, 'post', data=score_data, referer=self.ZF_URLS['LOGIN'], cookies=cookies, host=self.host)
        if resp is None or resp.text is None:
            api.logger.warning('[+] got %s cert score failed.' % student_id)
            return "[]"
        content = resp.text
        res = ZfParser.parse_zf_score(content)
        api.logger.info('[+] got %s score successfully.' % student_id)

        # 写至数据库
        print 'score1'
        self.insert_to_db('score', student_id, res)
        print 'score2'
        return res

    def _get_course(self, cookies, student_id):
        """
        获取本学期课程
        """
        pass

    def _get_cert_score(self, cookies, student_id):
        """
        获取等级考试成绩信息
        """
        pass
        # url = ZfParser.get_zf_urls(self.ZF_URLS['CERT_SCORE'], student_id)
        # resp = req(url, 'get', cookies=cookies, referer=self.ZF_URLS['LOGIN'])
        # if resp is None or resp.text is None:
        #     api.logger.warning('[+] got %s cert score failed.' % student_id)
        #     return "[]"
        # content = resp.text
        # res = ZfParser.parse_zf_cert_score(content)
        # api.logger.info('[+] got %s cert score successfully.' % student_id)
        #
        # # 写至数据库
        # print 'cert1'
        # rdb.set_trace()
        # self.insert_to_db('cert_score', student_id, res)
        # print 'cert2'
        # return res

    def _get_thesis(self, cookies, student_id):
        """
        获取毕业论文信息
        """
        pass

    def _get_img(self, cookies, student_id):
        """
        保存个人照片
        """
        img_url = ZfParser.get_zf_urls(self.ZF_URLS['IMG'], student_id)
        resp = req(img_url, 'get', referer=self.ZF_URLS['LOGIN'], cookies=cookies, host=self.host)
        if resp is None:
            return ''
        i = Image.open(StringIO(resp.content))
        if self.debug:
            i.save(student_id + '.jpg')
        api.logger.info('[+] got %s image successfully.' % student_id)
        url = save_to_qiniu(i)
        i.close()

        # 写至数据库
        print 'img1'
        self.insert_to_db('img_url', student_id, dict(img_url=img_url))
        print 'img2'
        return img_url

    def get_data(self, cookies=None, student_id=None):
        """
        并发爬取所有信息，实时返回info信息，需要把身份证后六位传给EhomeCrawler尝试登录。
        """
        api.logger.info('[*] start fetching data from zf for %s' % student_id)

        # 这里查的是最后的数据统计信息，不是原始信息。
        res = self.find_in_db('analysis', student_id=student_id)
        if res is not None and not res['analysis']['incomplete']:
            return res

        threads = []
        threads.extend([
            gevent.spawn(self._get_score, cookies, student_id),
            gevent.spawn(self._get_cert_score, cookies, student_id),
            gevent.spawn(self._get_thesis, cookies, student_id),
            gevent.spawn(self._get_course, cookies, student_id),
            gevent.spawn(self._get_img, cookies, student_id)
        ])

        gevent.joinall(threads)

        res = dict(score=threads[0].value,
                   cert_score=threads[1].value,
                   thesis=threads[2].value,
                   course=threads[3].value,
                   img_url=threads[4].value)

        # 进行分析处理后，写至数据库分析字段。
        # analysis = self.analyze(res, student_id)

        # TODO 返回分析后的数据 analysis
        return res

    def find_in_db(self, key_name, student_id=None):
        # rdb.set_trace()
        res = self.collection.find_one({'student_id': student_id}, {"_id": 0, key_name: 1})
        # key_name不存在的话，会返回{}空字典
        if not res:
            return None
        return res

    def insert_to_db(self, key_name, student_id, res):
        """
        TODO 原数据库中有的字段有值，而现在查询没有的，保留原有字段值。
        :return:
        """
        # FIXME incomplete 机制 怎么样做才最好？
        res['incomplete'] = False
        # FIXME 这里每次都需要重写一次student_id
        return \
            self.collection.update_one({"student_id": student_id},
                                       {'$set': {"student_id": student_id, key_name: res}},
                                       upsert=True) == 1

    def analyze(self, res, student_id):
        failed_courses_count = 0
        highest_score = 0
        highest_weight = 0
        highest_course = ''
        for x in res['score']['all_score']:
            if x[10] != '':
                failed_courses_count += 1
            try:
                highest = float(x[7])
                weight = float(x[6])
                if highest > highest_score:
                    highest_score = highest
                    highest_course = x[3]
                elif highest == highest_score and weight > highest_weight:
                    highest_score = highest
                    highest_course = x[3]
            except:
                continue

        res = dict(examed_courses_count=len(res['score']['all_score']),
                   failed_courses_count=failed_courses_count,
                   highest_course=dict(name=highest_course,
                                       score=highest_score))


        return json.dumps(res, ensure_ascii=False)

if __name__ == '__main__':
    zc = ZfCrawler(debug=True)
    _, cookies = zc.get_captcha(debug=True)
    captcha = raw_input('login captcha: ')
    login_data = dict(student_id=Config.TEST_STUDENT_ID,
                      zf_password=Config.TEST_ZF_PASSWORD,
                      zf_captcha=captcha)
    sid, _ = zc.login(login_data, cookies)
    j = zc.get_data(cookies, sid)
    import pprint

    pprint.pprint(j, indent=4)
    # print zc._get_cert_score(cookies, sid)
