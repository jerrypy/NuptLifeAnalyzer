#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by jerrypy at 16-1-12 下午11:39

import functools
import cPickle


def unpack_cookies(func):
    """解析cookies"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        kwargs['cookies'] = cPickle.loads(kwargs['cookies'])
        return func(*args, **kwargs)
    return wrapper


if __name__ == '__main__':
    @unpack_cookies
    def test(self, data, cookies=None):
        print cookies

    cookies = dict(test=1, hello=2)
    test(1, 2, cookies=cPickle.dumps(cookies))
