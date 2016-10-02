#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler


# init logger here
class ApiHandler(object):
    """日志"""
    def __init__(self):
        pass

    @property
    def logger(self, log_file='/var/log/youji/crawlers.log', log_level=logging.INFO, output_level=logging.INFO):
        logging.basicConfig(level=log_level,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            datefmt='%Y-%m-%d %a %H:%M:%S',
                            filename='%s' % log_file)
        logger = logging.getLogger("crawlers")
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        rt = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=10)
        rt.setLevel(output_level)
        rt.setFormatter(formatter)

        logger.addHandler(rt)
        logger.removeHandler(rt)
        return logger

api = ApiHandler()


def get_text(doc, tag_id, value=False):
    """
    beautifulsoup get_text() wrapper
    优雅地处理 doc.find() 为 None的情况

    :param doc: beautifulsoup doc
    :param tag_id: tag id
    :param value: 是否取tag中value属性的值
    :return:
    """
    res = doc.find(id=tag_id)
    if res is not None:
        if value:
            if 'value' in res.attrs:
                return res.attrs['value'].strip()
            else:
                # api.logger.warning('[-] tag: %s has no value attr.' % tag_id)
                return ''
        else:
            return res.get_text()
    else:
        # api.logger.error('[-] doc has no such tag: %s.' % tag_id)
        return ''


def save_to_qiniu(img):
    """
    文件上传至七牛
    :return: url
    """
    pass
