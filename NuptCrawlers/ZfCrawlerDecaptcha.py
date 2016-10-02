#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from PIL import Image
from StringIO import StringIO
from urlparse import urlparse
import json
import datetime
import gevent
from celery.contrib import rdb

from config import Config
from app_config import Config as APP_CONFIG
from NUPTCrawlerBase import NUPTCrawlerBase
from lib.util import api, save_to_qiniu
from lib.http import req
from lib.PageParser import ZfParser


class ZfCrawlerDecaptcha(NUPTCrawlerBase):
    """
    cookie是抓取验证码时候的cookie。

    每一个入口，都需要传入cookies和student_id，因为我们需要先展示
    验证码给用户，让用户自行输入，所以这样设计。
    能自动识别验证码后，可以与Lib和Ehome相同的设计。
    """

    def __init__(self, db=None, debug=False):
        super(ZfCrawlerDecaptcha, self).__init__(debug=debug)
        self.ZF_URLS = Config.ZF_URLS
        self.host = urlparse(self.ZF_URLS['LOGIN']).netloc
        self.cookies = None
        self.img = None
        self.vs_regex = r'<input type="hidden" name="__VIEWSTATE" value="((.[^\s])*)" />'
        self.db = db
        self.collection = db.zf

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

    def _decaptcha(self, img=None):

        if self.debug:
            if img is None:
                q = req(Config.ZF_URLS['CAPTCHA'], 'get')
                if q is None:
                    return ''
                img = q.content
                self.cookies = q.cookies
            i = Image.open(StringIO(img))
            i.save('captcha.gif')
            i.close()

            cap = raw_input('captcha: ')
            return cap

        # TODO 计算调用次数，错误次数
        if img is None:
            q = req(Config.ZF_URLS['CAPTCHA'], 'get')
            if q is None:
                return ''

            self.img = captcha = q.content
            self.cookies = q.cookies
        else:
            captcha = img

        if captcha is None:
            return ''

        data = {
            'file': captcha
        }
        api.logger.info('[*] try cracking the captcha...')
        p = req(Config.DECAPTCHA_URL, 'post', files=data)
        if p is None:
            api.logger.error('[-] decaptcha service error!')
            return ''
        api.logger.info('[+] got captcha ' + p.text)
        return p.text

    def _get_viewstate(self, url, return_content=False):
        """
        获取表单viewstate
        """
        resp = req(url, 'get', referer=self.ZF_URLS['LOGIN'], cookies=self.cookies)
        if resp is None:
            return '', Config.SERVER_MSG['SERVER_ERROR']
        res = re.search(self.vs_regex, resp.text, re.S)
        if res is None:
            return '', Config.SERVER_MSG['SERVER_ERROR']
        viewstate = res.group(1)

        if return_content:
            return resp.text, viewstate
        return viewstate

    def _login(self, login_data=None):
        """
        登录正方
        :param login_data:
        :return: (student_id, 登录结果)
        """
        viewstate = self._get_viewstate(self.ZF_URLS['LOGIN'])
        if viewstate == Config.SERVER_MSG['SERVER_ERROR']:
            return '', Config.SERVER_MSG['SERVER_ERROR']
        self.student_id = student_id = login_data['student_id']
        login_data = {
            '__VIEWSTATE': viewstate,
            'txtUserName': student_id,
            'TextBox2': login_data['zf_password'],
            'txtSecretCode': '',
            'RadioButtonList1': '学生',
            'Button1': '登录',
            'lbLanguange': '',
            'hidPdrs': '',
            'hidsc': ''
        }

        # TODO: 3次仍失败，需作相应处理
        crack_time = 1

        while True and crack_time <= 1:
            login_data['txtSecretCode'] = self._decaptcha(self.img)
            if login_data['txtSecretCode'] == '':
                # 第三方解码平台错误
                return '', Config.SERVER_MSG['WRONG_CAPTCHA']

            resp = req(self.ZF_URLS['LOGIN'], 'post', referer=self.ZF_URLS['LOGIN'], data=login_data, cookies=self.cookies)

            if resp is None:
                return '', Config.SERVER_MSG['SERVER_ERROR']
            if resp.url.startswith(self.ZF_URLS['LOGIN_SUCCESS']):
                api.logger.info('[+] ID: %s login zf successfully.' % (login_data['txtUserName']))
                msg = Config.SERVER_MSG['LOGIN_SUCCESS']
                break
            elif self.ZF_URLS['WRONG_CAPTCHA_FINGER'] in resp.text:
                msg = Config.SERVER_MSG['WRONG_CAPTCHA']
                crack_time += 1
            elif self.ZF_URLS['INVALID_CAPTCHA_FINGER'] in resp.text:
                msg = Config.SERVER_MSG['INVALID_USERNAME']
                break
            elif self.ZF_URLS['WRONG_PASS_FINGER'] in resp.text:
                api.logger.warning('[-] ID: %s login zf failed.' % (login_data['txtUserName']))
                msg = Config.SERVER_MSG['WRONG_PASSWORD']
                break
            elif self.ZF_URLS['COMMENT'] in resp.text:
                api.logger.warning('[-] need to comment for classes.')
                msg = Config.SERVER_MSG['COMMENT_TIME']
                break
            else:
                msg = Config.SERVER_MSG['SERVER_ERROR']
                break
        return login_data['txtUserName'], msg

    def login(self, login_data=None):
        return self._login(login_data=login_data)

    def get_personal_info(self, student_id):
        """
        获取个人信息
        """
        # rdb.set_trace()
        if self.collection is None:
            self.collection = getattr(self.db, 'zf')
        # 先找数据库
        res = self.find_in_db('info')
        # 如果数据库中没有记录，或者记录是不完整的，才尝试查询
        if res is not None and not res['info']['incomplete']:
            return res['info']

        url = ZfParser.get_zf_urls(self.ZF_URLS['INFO'], student_id)
        resp = req(url, 'get', referer=self.ZF_URLS['LOGIN'], cookies=self.cookies)
        if resp is None:
            api.logger.warning('[-] got %s personal info failed.' % student_id)
            return Config.SERVER_MSG['SERVER_ERROR']
        content = resp.text
        res = ZfParser.parse_zf_info(content)
        api.logger.info('[+] got %s personal info successfully.' % student_id)

        # 写至数据库
        self.insert_to_db('info', res, date=True)


        return res

    def _get_score(self, student_id):
        """
        获取成绩信息
        """
        url = ZfParser.get_zf_urls(self.ZF_URLS['SCORE'], student_id)
        viewstate = self._get_viewstate(url)
        score_data = {
            '__VIEWSTATE': viewstate,
            'ddlXN': '',
            'ddlXQ': '',
            'Button2': '在校学习成绩查询'
        }
        resp = req(url, 'post', data=score_data, referer=self.ZF_URLS['LOGIN'], cookies=self.cookies, host=self.host)
        if resp is None or resp.text is None:
            api.logger.warning('[+] got %s score failed.' % student_id)
            return "[]"
        content = resp.text
        res = ZfParser.parse_zf_score(content)
        api.logger.info('[+] got %s score successfully.' % student_id)

        # 写至数据库
        self.insert_to_db('score', res)
        return res

    def _get_course(self, student_id):
        """
        获取本学期课程
        """
        url = ZfParser.get_zf_urls(self.ZF_URLS['COURSE'], student_id)
        content, viewstate = self._get_viewstate(url, return_content=True)
        if content == '':
            # get_viewstate失败
            api.logger.error('[-] got %s course failed by get_viewstate!' % student_id)
            return {}

        res = ZfParser.parse_zf_course(content, viewstate, url, self.cookies, self.ZF_URLS['LOGIN'])

        api.logger.info('[+] got %s course successfully.' % student_id)

        self.insert_to_db('course', res)
        return res

    def _get_cert_score(self, student_id):
        """
        获取等级考试成绩信息
        """
        url = ZfParser.get_zf_urls(self.ZF_URLS['CERT_SCORE'], student_id)
        resp = req(url, 'get', cookies=self.cookies, referer=self.ZF_URLS['LOGIN'])
        if resp is None or resp.text is None:
            api.logger.warning('[-] got %s cert score failed.' % student_id)
            return "[]"
        content = resp.text
        res = ZfParser.parse_zf_cert_score(content)
        api.logger.info('[+] got %s cert score successfully.' % student_id)

        # 写至数据库
        self.insert_to_db('cert_score', res)
        return res

    def _get_thesis(self, student_id):
        """
        获取毕业论文信息
        """
        pass

    def _get_img(self, student_id):
        """
        保存个人照片
        """
        img_url = ZfParser.get_zf_urls(self.ZF_URLS['IMG'], student_id)
        resp = req(img_url, 'get', referer=self.ZF_URLS['LOGIN'], cookies=self.cookies, host=self.host)
        if resp is None:
            return ''
        i = Image.open(StringIO(resp.content))
        if self.debug:
            i.save(student_id + '.jpg')
        api.logger.info('[+] got %s image successfully.' % student_id)
        url = save_to_qiniu(i)
        i.close()

        # 写至数据库
        self.insert_to_db('img_url', dict(img_url=img_url))
        return img_url

    def get_data(self, student_id=None):
        """
        并发爬取所有信息，实时返回info信息，需要把身份证后六位传给EhomeCrawler尝试登录。
        """
        student_id = self.student_id
        api.logger.info('[*] start fetching data from zf for %s' % student_id)

        # 这里查的是最后的数据统计信息，不是原始信息。
        res = self.find_in_db('analysis')
        if res is not None and not res['analysis']['incomplete']:
            if (datetime.datetime.now() - self.find_in_db('fetch_date')['fetch_date']).days > APP_CONFIG.ZF_DATA_TTL:
                pass
            else:
                return res

        threads = []
        threads.extend([
            gevent.spawn(self._get_score, student_id),
            gevent.spawn(self._get_cert_score, student_id),
            gevent.spawn(self._get_thesis, student_id),
            gevent.spawn(self._get_course, student_id),
            gevent.spawn(self._get_img, student_id)
        ])

        gevent.joinall(threads)

        res = dict(score=threads[0].value,
                   cert_score=threads[1].value,
                   thesis=threads[2].value,
                   course=threads[3].value,
                   img_url=threads[4].value)

        # 进行分析处理后，写至数据库分析字段。
        analysis = self.analyze(res, student_id)
        if analysis is None:
            # 数据获取不完全
            return None
        self.insert_to_db('analysis', analysis)

        return {'analysis': analysis}


    def analyze(self, res, student_id):
        """数据分析"""
        # TODO 处理有些抓取失败，返回结果空的情况

        api.logger.info('[*] start analyzing %s zf data...' % student_id)

        if res['course'] == {} or res['score'] == "[]" or res['course'] is None or res['score'] is None:
            return None
        # 获取第一堂课
        key = res['course'].keys()
        key.remove('incomplete') # 获取学年学期键名
        courses = res['course'][key[0]]
        first_course = courses[0]
        first_course_failed = False # 第一门课挂了没有
        first_course_failing = False # 第一门课还挂着
        min_time = first_course['course_time']
        for i in courses:
            if i['course_time'].startswith('周'.decode('utf-8')) and i['course_time'] < min_time:
                first_course = i
                min_time = first_course['course_time']
        for i in res['score']['fail_course']:
            if first_course['course_name'] == i[1]:
                first_course_failing = True

        # 分析英语A/B班
        english_class_a = True
        all_course_score = res['score']['all_score']
        for c in all_course_score:
            # 通过课程中是否有大学英语I来判断
            if c[3] == '大学英语Ⅰ'.decode('utf-8'):
                english_class_a = False
                break


        failed_courses_count = 0
        highest_score = 0 # 最高成绩
        highest_weight = 0
        highest_course = ''
        first_course_score = 0 # 设个默认值，防止出错
        for x in all_course_score:
            if x[3] == first_course['course_name']:
                if x[10] != '':
                    first_course_failed = True
                first_course_score = x[8] # 第一门课分数
            if x[10] != '':
                failed_courses_count += 1 # 补考成绩有分数，挂过的科目
            try:
                # TODO 遍历算法是否可以改进
                highest = float(x[8]) # 分数
                weight = float(x[7]) # 绩点作权重
                if highest > highest_score:
                    highest_score = highest
                    highest_course = x[3]
                elif highest == highest_score and weight > highest_weight:
                    highest_score = highest
                    highest_course = x[3]
            except ValueError:
                # 有些成绩为合格等非浮点数，则忽略
                continue

        res = dict(examed_courses_count=len(res['score']['all_score']),
                   failed_courses_count=failed_courses_count,
                   fail_course=res['score']['fail_course'],
                   english_class_a=english_class_a,
                   highest_course=dict(name=highest_course,
                                       score=highest_score),
                   first_course=first_course,
                   first_course_failed=first_course_failed,
                   first_course_score=first_course_score,
                   first_course_failing=first_course_failing)


        return res

if __name__ == '__main__':
    from pymongo import MongoClient
    from app_config import Config as APP_CONFIG

    conn = MongoClient(APP_CONFIG.MONGO_URI)
    db = conn.youji
    db.authenticate(APP_CONFIG.MONGO_USER, APP_CONFIG.MONGO_PWD)
    zc = ZfCrawlerDecaptcha(debug=True, db=db)
    login_data = dict(student_id='',
                      zf_password='')
    sid, _ = zc.login(login_data)
    print sid, _
    # j = zc.get_data(sid)
    if _ == 1:
        res = zc._get_course('')
        print res
    # print zc._get_cert_score(cookies, sid)
