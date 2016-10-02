#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


class Config:

    def __init__(self):
        pass

    ZF_DATA_TTL = 10 # 单位days 正方数据过期时间
    LIB_DATA_TTL = 5 # 图书馆数据过期时间
    EHOME_DATA_TTL = 1 # 智慧校园数据过期时间
    ADMIN_STUDENT_ID = ''

    # 会话相关配置
    SECRET_KEY = os.environ.get('YOUJI_SECRET_KEY') or 'ljfs@#$(fjf'
    YOUJI_SESSION_PREFIX = 'youji_session:'
    REDIS_SESSION_CONN = 'redis://localhost:6379/0'

    # 邮件配置相关
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = '587'
    MAIL_USERNAME = os.environ.get('YOUJI_MAIL_USERNAME') or 'Youji Admin'
    MAIL_PASSWORD = os.environ.get('YOUJI_MAIL_PASSWORD') or ''

    YOUJI_MAIL_SUBJECT_PREFIX = '[Youji]'
    YOUJI_MAIL_SENDER = 'Youji Admin <root@jerrywin.com>'
    YOUJI_ADMIN = os.environ.get('YOUJI_ADMIN') or ''

    # celery config
    CELERY_BROKER_URL = 'redis://localhost:6379/1'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
    CELERY_ACCEPT_CONTENT = ['pickle', 'json']
    CELERY_TASK_RESULT_EXPIRES = 60*60*24*3  # 3 days

    # per: http://docs.celeryproject.org/en/latest/userguide/tasks.html#disable-rate-limits-if-they-re-not-used
    CELERY_DISABLE_RATE_LIMITS = True

    # celery 路由
    # http://docs.celeryproject.org/en/latest/userguide/routing.html#manual-routing
    CELERY_ROUTES = {
        'app.main.tasks.debug': {'queue': 'debug'},
        'app.main.tasks.zf_login': {'queue': 'zf_login'},
        'app.main.tasks.zf_crawler': {'queue': 'zf_crawler'},
        'app.main.tasks.zf_crawler_decaptcha': {'queue': 'zf_crawler_decaptcha'},
        'app.main.tasks.lib_crawler': {'queue': 'lib_crawler'},
        'app.main.tasks.ehome_crawler': {'queue': 'ehome_crawler'},
        'app.main.tasks.try_youji': {'queue': 'try_youji'}
    }

    # MongoDB 相关配置
    MONGO_HOST = ''
    MONGO_PORT = ''
    MONGO_DB_NAME = 'youji'
    MONGO_USER = ''
    MONGO_PWD = ''
    MONGO_URI = 'mongodb://127.0.0.1:27017/youji'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
