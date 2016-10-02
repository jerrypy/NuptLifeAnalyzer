#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    获取天气信息。

    （改的很乱了，不知道怎么整理）
"""

import requests
from bs4 import BeautifulSoup

import gevent
from app_config import Config as APP_CONFIG

from pymongo import MongoClient

import datetime

start_time = datetime.datetime.now()
print 'start at ' + str(start_time)

conn = MongoClient(APP_CONFIG.MONGO_URI)
db = conn.youji
db.authenticate(APP_CONFIG.MONGO_USER, APP_CONFIG.MONGO_PWD)
weather = db.nj_weather

url_prefix = 'http://www.tianqihoubao.com/lishi/nanjing/month/'

def get_data(date):
    x = 7 if date == 201600 else 12
    for xi in range(x):
        # date += 1

        text = requests.get(url_prefix+str(date)+'.html').text
        doc = BeautifulSoup(text, 'lxml')
        l = doc.find('table').text.split()[4:]
        for i in range(0, len(l), 10):
            try:
                weather.insert({'date': l[i],
                                'weather1': l[i+1],
                                'weather2:': l[i+2][1:],
                                'temp_high': l[i+3],
                                'temp_low': l[i+5],
                                'wind': l[i+7] + ' ' +l[i+6]})
            except IndexError:
                print 'error ' + str(date)
                pass
        print 'finish ' + str(date)

# threads = []
# threads.extend([
#     gevent.spawn(get_data, 201100),
#     gevent.spawn(get_data, 201200),
#     gevent.spawn(get_data, 201300),
#     gevent.spawn(get_data, 201400),
#     gevent.spawn(get_data, 201500),
#     gevent.spawn(get_data, 201600),
#     ])
#
# gevent.joinall(threads)
#
# end_time = datetime.datetime.now()
# delta = end_time - start_time
#
# print 'end at ' + str(end_time)
# print 'spend ' + str(delta.seconds) + ' seconds'

# get_data(201606)

# s = datetime.date(2011,01,01)
# e = datetime.date(2016,7,18)
# delta = e - s
# old_l = []
# l = []
# for i in range(delta.days):
#     old_l.append((s + datetime.timedelta(i)).strftime('%Y年%m月%d日').decode('utf-8'))
#
# res = weather.find()
# for i in res:
#     l.append(i['date'])
#
# print set(old_l) - set(l)

# 今天抓去明天的
def get_tomorrow():
    wurl = 'http://op.juhe.cn/onebox/weather/query?dtype=json&key=1059c98274788923f01649fc74849df6&cityname=南京'

    res = requests.get(wurl)
    if res is None or res.json()['reason'] != 'successed!':
        print 'fetch weather error!!!'

    w = res.json()['result']['data']['weather'][1]

    weather.insert({
        'date': datetime.datetime.strptime(w['date'], '%Y-%m-%d').strftime('%Y年%m月%d日'),
        'weather1': w['info']['day'][1],
        'weather2': w['info']['night'][1],
        'temp_high': w['info']['day'][2].encode('utf-8')+'℃',
        'temp_low': w['info']['night'][2].encode('utf-8')+'℃',
        'wind': w['info']['day'][4].replace(' ', '') + ' ' + w['info']['day'][3]
    })



# weather.insert({
#     'date': '2016年07月18日',
#     'weather1': '雷阵雨',
#     'weather2': '雷阵雨',
#     'temp_low': '26℃',
#     'temp_high': '31℃',
#     'wind': '3-4级 东南风'
# })
def analyze():
    rainy_day = cloudy_day = sunny_day = snowy_day = overcast_day = frogy_day = 0
    unknown_day = []
    res = weather.find()
    for i in res:
        if '雨'.decode('utf-8') in i['weather1']:
            rainy_day += 1
        elif '云'.decode('utf-8') in i['weather1']:
            cloudy_day += 1
        elif '雪'.decode('utf-8') in i['weather1']:
            snowy_day += 1
        elif '晴'.decode('utf-8') in i['weather1']:
            sunny_day += 1
        elif '阴'.decode('utf-8') in i['weather1']:
            overcast_day += 1
        elif '雾'.decode('utf-8') in i['weather1']:
            frogy_day += 1
        else:
            unknown_day.append(i['date'])
            print i['date'] + '   ' + i['weather1']

    print '雨天 ' + str(rainy_day)
    print '多云 ' + str(cloudy_day)
    print '下雪 ' + str(snowy_day)
    print '晴天 ' + str(sunny_day)
    print '阴天 ' + str(overcast_day)
    print '雾天 ' + str(frogy_day)
    print 'total: ' + str(rainy_day+cloudy_day+sunny_day+snowy_day+overcast_day+frogy_day)

    weather.insert({
        'name': 'analysis',
        'rainy_day': rainy_day,
        'cloudy_day': cloudy_day,
        'snowy_day': snowy_day,
        'sunny_day': sunny_day,
        'overcast_day': overcast_day,
        'frogy_day': frogy_day,
        'unknown': unknown_day
    })


if __name__ == '__main__':
    analyze()
    pass