#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
http操作相关
"""

import requests
from copy import deepcopy
try:
    from config import Config
    from util import api
except ImportError:
    from ..config import Config
    from .util import api


def req(url, method, **kwargs):
    """
    requests封装函数，处理额外的参数字段。

    :param url: 目标地址
    :param method: http方法
    :param kwargs: 参数
    :return: requests.Response or None
    """
    headers = deepcopy(Config.HUMAN_HEADERS)
    if 'referer' in kwargs:
        headers.update({'Referer': kwargs['referer']})
        del kwargs['referer']
    if 'host' in kwargs:
        headers.update({'Host': kwargs['host']})
        del kwargs['host']
    kwargs.update({'headers': headers})
    try:
        kwargs.update({"timeout": 10, "verify": False})
        resp = getattr(requests, method)(url, **kwargs)
    except Exception as e:
        api.logger.error("[-] url: %s, error: %s" % (url, str(e)))
        return None

    return resp


class CODE:

    def __init__(self):
        pass

    TASK_PUBLISHED = {
        'code': 202,
        'msg': 'Task Published'
    }

    BAD_REQUEST = {
        'code': 400,
        'msg': 'Bad Request'
    }

    SERVER_ERROR = {
        'code': 500,
        'msg': 'Server Error'
    }

    TOO_YOUNG = {
        'code': 403,
        'msg': 'Too Young, Too Naive'
    }

    SHAME_ON_YOU = {
        'code': 401,
        'msg': ''
    }
