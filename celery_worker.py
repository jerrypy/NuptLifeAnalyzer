#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by jerrypy at 16-1-12 上午12:01

"""
工厂模式下celery的初始化。

参考： http://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern
"""

import os
from app import celery, create_app


app = create_app(os.getenv('YOUJI_CONFIG') or 'default')
app.app_context().push()
