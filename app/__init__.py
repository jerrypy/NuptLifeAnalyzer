#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Nupt Life Analyzer 南邮时光机
    ~~~~~

    Cherish everything you have. ^ ^

    :copyright: (c) 2016 by jerrypy<root@jerrywin.com>.
    :license: MIT, see LICENSE for more details.
"""

from celery import Celery
from flask import Flask
from flask.ext.mail import Mail
from flask.ext.bootstrap import Bootstrap

from app_config import config, Config
from redis_session import RedisSessionInterface

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL, backend=Config.CELERY_RESULT_BACKEND)
mail = Mail()
bootstrap = Bootstrap()


def create_app(config_name):
    app = Flask(__name__)
    app.session_interface = RedisSessionInterface(prefix=Config.YOUJI_SESSION_PREFIX)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    celery.conf.update(app.config)
    bootstrap.init_app(app)
    mail.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
