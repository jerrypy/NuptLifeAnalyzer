#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全部视图定义。
"""

import cPickle
from flask import render_template, request, jsonify, session, url_for
from NuptCrawlers.lib.http import CODE
from NuptCrawlers.ZfCrawler import ZfCrawler
from NuptCrawlers.config import Config as CRAWLER_CONFIG
from . import main
from .forms import ZfLoginForm
import tasks


@main.route('/')
def index():
    """首页视图"""
    form = ZfLoginForm()
    return render_template('index.html', form=form)


# @main.route('/about')
# def about():
#     """关于页面"""
#     return render_template('about.html')

# @main.route('/captcha.aspx')
# def captcha():
#     """
#     验证码视图
#
#     这个入口比较容易受D
#     :return: 图片流
#     """
#     img, cookies = ZfCrawler.get_captcha()
#     # 正方cookies存入session
#     session['zf_cookies'] = cPickle.dumps(cookies)
#     return img


@main.route('/try', methods=['POST'])
def try_youji():
    """非南邮用户体验"""
    task = tasks.try_youji.apply_async()
    return \
        jsonify(CODE.TASK_PUBLISHED), \
        202, \
        {'Location': url_for('.try_youji_status', task_id=task.id)}


@main.route('/try_youji_status/<task_id>')
def try_youji_status(task_id):
    """游客任务status接口"""
    task = tasks.try_youji.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'zf_data': task.result.get('zf_data'),
            'lib_data': task.result.get('lib_data'),
            'ehome_data': task.result.get('ehome_date')
        }
    else:
        response = {
            'state': task.state
        }

    return jsonify(response)


# @main.route('/zf_login', methods=['POST'])
# def zf_login():
#     """正方登录接口"""
#     student_id = request.form.get('student_id')
#     password = request.form.get('password')
#     captcha = request.form.get('captcha')
#
#     if student_id and password and captcha:
#         login_data = dict(student_id=student_id,
#                           zf_password=password,
#                           zf_captcha=captcha)
#         cookies = session.get('zf_cookies')
#         if cookies is None:
#             # 未访问captcha直接访问该入口
#             return jsonify(CODE.BAD_REQUEST), 400
#         task = tasks.zf_login.apply_async(args=[login_data],
#                                           kwargs={'cookies': cookies})
#         return \
#             jsonify(CODE.TASK_PUBLISHED), \
#             202, \
#             {'Location': url_for('.zf_login_status', task_id=task.id)}
#
#     else:
#         # 表单内容不完整
#         return jsonify(CODE.BAD_REQUEST), 400
#
#
# @main.route('/get_zf_data', methods=['POST'])
# def zf_data():
#     """正方爬虫接口"""
#     cookies = session.get('zf_cookies')
#     student_id = session.get('student_id')
#     if cookies and student_id:
#         task = tasks.zf_crawler.apply_async(args=[student_id],
#                                             kwargs={'cookies': cookies})
#         return \
#             jsonify(CODE.TASK_PUBLISHED), \
#             202, \
#             {'Location': url_for('.zf_crawler_status', task_id=task.id)}
#     else:
#         # 没有成功登录，禁止访问该入口
#         return CODE.BAD_REQUEST


@main.route('/get_zf_data_decaptcha', methods=['POST'])
def zf_data_decaptcha():
    """正方爬虫免验证码入口"""
    student_id = request.form.get('student_id')
    password = request.form.get('password')

    if student_id and password:
        login_data = dict(student_id=student_id,
                          zf_password=password)

        # 登录student_id写入cookies，防止后面越权或者未经过正方登录就访问其他入口
        session['student_id'] = student_id

        task = tasks.zf_crawler_decaptcha.apply_async(args=[login_data])
        return \
            jsonify(CODE.TASK_PUBLISHED), \
            202, \
            {'Location': url_for('.zf_crawler_decaptcha_status', task_id=task.id)}
    else:
        return jsonify(CODE.BAD_REQUEST), 400


@main.route('/get_lib_data', methods=['POST'])
def lib_data():
    """图书馆爬虫接口"""

    student_id = session.get('student_id') # 获取cookies中的student_id
    password = request.form.get('password')
    if password is None:
        password = student_id
    if student_id and password:
        login_data = dict(student_id=student_id,
                          password=password)
        task = tasks.lib_crawler.apply_async(args=[login_data])
        return \
            jsonify(CODE.TASK_PUBLISHED), \
            202, \
            {'Location': url_for('.lib_crawler_status', task_id=task.id)}
    else:
        # 表单内容不完整
        return jsonify(CODE.BAD_REQUEST), 400


@main.route('/get_ehome_data', methods=['POST'])
def ehome_data():
    """智慧校园爬虫接口
        201610 学校关闭该接口，该爬虫并没有工作
    """

    student_id = session.get('student_id') # 获取cookies中的student_id
    password = request.form.get('password')
    start_date = request.form.get('start_date')
    cardno = request.form.get('cardno')
    if student_id and password:
        login_data = dict(student_id=student_id,
                          password=password)
        task = tasks.ehome_crawler.apply_async(args=[login_data, start_date, cardno])
        return \
            jsonify(CODE.TASK_PUBLISHED), \
            202, \
            {'Location': url_for('.ehome_crawler_status', task_id=task.id)}
    else:
        return CODE.BAD_REQUEST


# @main.route('/zf_login_status/<task_id>')
# def zf_login_status(task_id):
#     """正方登录实时结果查询接口"""
#     task = tasks.zf_login.AsyncResult(task_id)
#     if task.state == 'SUCCESS' and task.info.get('code', ''):
#         response = {
#             'state': task.state,
#             'code': task.info.get('code')
#         }
#         if task.info.get('code') == CRAWLER_CONFIG.SERVER_MSG['LOGIN_SUCCESS']:
#             # 登录成功， student_id存入session
#             session['student_id'] = task.info.get('student_id')
#     else:
#         response = {
#             'state': task.state,
#             'code': CRAWLER_CONFIG.SERVER_MSG['WAITING']
#         }
#     return jsonify(response)


# @main.route('/zf_crawler_status/<task_id>')
# def zf_crawler_status(task_id):
#     """正方爬虫实时结果查询接口"""
#     task = tasks.zf_crawler.AsyncResult(task_id)
#     if task.state == 'INFO_GOT':
#         response = {
#             'state': task.state,
#             'zf_info': task.info.get('zf_info')
#         }
#     elif task.state == 'SUCCESS':
#         response = {
#             'state': task.state,
#             'zf_info': task.info.get('zf_info'),
#             'data': task.info.get('data')
#         }
#     else:
#         response = {
#             'state': task.state,
#         }
#     return jsonify(response)


@main.route('/zf_crawler_decaptcha_status/<task_id>')
def zf_crawler_decaptcha_status(task_id):
    """正方爬虫实时结果查询接口"""
    task = tasks.zf_crawler_decaptcha.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        if task.result.get('code') is not None:
            response = {
                'state': task.state,
                'code': task.result.get('code'),
                'msg': task.result.get('msg')
            }
        else:
            response = {
                'state': task.state,
                'zf_info': task.result.get('zf_info'),
                'data': task.result.get('data')
            }
    elif task.state == 'INFO_GOT':
        response = {
            'state': task.state,
            'zf_info': task.result.get('zf_info')
        }
    else:
        response = {
            'state': task.state
        }
    return jsonify(response)



@main.route('/lib_crawler_status/<task_id>')
def lib_crawler_status(task_id):
    """图书馆爬虫实时结果查询接口"""
    task = tasks.lib_crawler.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        #: 任务终止的两种情况：
        #:  1. 登录失败
        #:  2. 抓取完毕
        if task.result.get('login_res') is not None:
            # 登录失败
            response = {
                'state': task.state,
                'code': task.result.get('login_res'),
                'msg': task.result.get('msg')
            }
        else:
            # 抓取完成
            response = {
                'state': task.state,
                'data': task.result.get('data')
            }
    else:
        response = {
            'state': task.state,
        }
    return jsonify(response)


@main.route('/ehome_crawler_status/<task_id>')
def ehome_crawler_status(task_id):
    """智慧校园爬虫实时结果查询接口"""
    task = tasks.ehome_crawler.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        #: 任务终止的两种情况：
        #:  1. 登录失败
        #:  2. 抓取完毕
        if task.result.get('login_res') is not None:
            # 登录失败
            response = {
                'state': task.state,
                'code': task.result.get('login_res'),
                'msg': task.result.get('msg')
            }
        else:
            # 抓取完成
            response = {
                'state': task.state,
                'data': task.result.get('data')
            }
    else:
        response = {
            'state': task.state,
        }
    return jsonify(response)


@main.route('/debug')
def debug():
    """调试接口"""
    from NuptCrawlers.EhomeCrawler import EhomeCrawler
    from pymongo import MongoClient
    from NuptCrawlers.config import Config
    from app_config import Config as APP_CONFIG
    conn = MongoClient(APP_CONFIG.MONGO_URI)
    db = conn.youji
    db.authenticate('youji_admin', 'swing4life')
    ec = EhomeCrawler(db=db, debug=True)
    ec._login(login_data={'student_id': Config.TEST_STUDENT_ID,
                          'password': Config.TEST_EHOME_PASSWORD})
    return jsonify(ec._get_rec('2012-09-01'))


@main.route('/test')
def test():
    return render_template('test.html')
