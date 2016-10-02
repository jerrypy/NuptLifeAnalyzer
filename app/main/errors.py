#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义错误页面。
"""

from flask import render_template
from . import main


@main.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500
