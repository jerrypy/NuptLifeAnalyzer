#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
页面解析操作
"""

from __future__ import absolute_import
from bs4 import BeautifulSoup
import re
from .http import req
from .util import api

try:
    from ..config import Config
    from .util import *
except Exception:
    from NuptCrawlers.config import Config
    from NuptCrawlers.lib.util import *


class ZfParser(object):
    @staticmethod
    def get_zf_urls(url, student_id):
        return url + '?xh=' + student_id

    @staticmethod
    def parse_zf_info(content):
        """
        解析个人信息页面
        :return:
        """
        doc = BeautifulSoup(content, 'lxml')
        xm = get_text(doc, 'xm')
        telnum = get_text(doc, 'TELNUMBER', True)  # value
        gender = get_text(doc, 'lbl_xb')
        entrance_date = get_text(doc, 'lbl_rxrq')
        birth_date = get_text(doc, 'lbl_csrq')
        middle_school = get_text(doc, 'lbl_byzx')
        nation = get_text(doc, 'lbl_mz')
        dorm_id = get_text(doc, 'lbl_ssh')
        native_place = get_text(doc, 'lbl_jg')
        email = get_text(doc, 'dzyxdz', True)  # value
        politics_status = get_text(doc, 'lbl_zzmm')
        phone_num = get_text(doc, 'lxdh', True)  # value
        origin_place = get_text(doc, 'lbl_lydq')

        #: 暂时仅用于取后六位，尝试登录智慧校园
        #: 这个字段很重要，因为要作为默认密码发送给智慧校园爬虫
        #: 没有正常获取到需重试
        id_num = get_text(doc, 'lbl_sfzh')[-6:] or '000000'  # 即使获取失败，也传一个错误内容，前端容错。

        edu_level = get_text(doc, 'lbl_CC')
        academy = get_text(doc, 'lbl_xy')
        major = get_text(doc, 'lbl_zymc')
        is_athlete = get_text(doc, 'lbl_SFGSPYDY')
        class_id = get_text(doc, 'lbl_xzb')
        school_length = get_text(doc, 'lbl_xz')
        grade = get_text(doc, 'lbl_dqszj')

        # 统一日期格式，保持与智慧校园所用一致
        try:
            entrance_date = entrance_date[:4] + '-' + entrance_date[4:6] + '-' + entrance_date[6:]
        except:
            if grade != '':
                entrance_date = grade + '-08-01'
            else:
                entrance_date = '2012-09-01'  # 默认是2012届的最早时间

        return dict(student_name=xm,
                    telnum=telnum,
                    gender=gender,
                    entrance_date=entrance_date,
                    birth_date=birth_date,
                    middle_school=middle_school,
                    nation=nation,
                    dorm_id=dorm_id,
                    native_place=native_place,
                    email=email,
                    politics_status=politics_status,
                    phone_num=phone_num,
                    origin_place=origin_place,
                    id_num=id_num,
                    edu_level=edu_level,
                    academy=academy,
                    major=major,
                    is_athlete=is_athlete,
                    class_id=class_id,
                    school_length=school_length,
                    grade=grade)

    @staticmethod
    def parse_zf_score(content):
        """
        解析成绩页面
        :return:
        {
            "all_score": [[],[]],  # 所有科目成绩
            "all_sum": [[],[]],    # 统计
            "fail_course": [[],[]],# 至今未通过课程
            "number_of_class": "", # 专业人数
            "ave_gpa": "",         # 平均学分绩点
            "all_gpa": ""          # 学分绩点总和
        }
        """
        res = {}
        doc = BeautifulSoup(content, 'lxml')

        # 成绩表格
        score_table = doc.find(id='Datagrid1')
        all_score = []
        if score_table is None:
            pass
        else:
            trs = score_table.find_all('tr')
            for tr in trs[1:]:
                tds = tr.find_all('td')
                score = []
                for td in tds:
                    text = td.get_text().strip()
                    score.append(text)
                all_score.append(score)
        res['all_score'] = all_score

        # 合计表格
        sum_table1 = doc.find(id='Datagrid2')
        all_sum = []
        if sum_table1 is None:
            pass
        else:
            trs = sum_table1.find_all('tr')
            for tr in trs[1:-1]:
                tds = tr.find_all('td')
                score = []
                for td in tds:
                    text = td.get_text().strip()
                    score.append(text)
                all_sum.append(score)

        sum_table2 = doc.find(id='DataGrid6')
        if sum_table2 is None:
            pass
        else:
            trs = sum_table2.find_all('tr')

            for tr in trs[1:-1]:
                tds = tr.find_all('td')
                score = []
                for td in tds:
                    text = td.get_text().strip()
                    score.append(text)
                all_sum.append(score)
        res['all_sum'] = all_sum

        # 至今未通过课程
        fail_table = doc.find(id='Datagrid3')
        fail_course = []
        if fail_table is None:
            pass
        else:
            trs = fail_table.find_all('tr')

            for tr in trs[1:]:
                tds = tr.find_all('td')
                course = []
                for td in tds:
                    text = td.get_text().strip()
                    course.append(text)
                fail_course.append(course)
        res['fail_course'] = fail_course

        # sum
        count = doc.find(id='zyzrs')
        ave_gpa = doc.find(id='pjxfjd')
        all_gpa = doc.find(id='xfjdzh')

        count = count.get_text() if count is not None else ''
        ave_gpa = ave_gpa.get_text() if ave_gpa is not None else ''
        all_gpa = all_gpa.get_text() if ave_gpa is not None else ''

        a = re.search('\d+', count)
        b = re.search('\d+\.\d+', ave_gpa)
        c = re.search('\d+\.\d+', all_gpa)

        number_of_class = a.group() if a is not None else '0'
        ave_gpa = b.group() if b is not None else '0.0'
        all_gpa = c.group() if c is not None else '0.0'

        res['number_of_class'] = number_of_class
        res['ave_gpa'] = ave_gpa
        res['all_gpa'] = all_gpa

        return res

    @staticmethod
    def parse_zf_cert_score(content):
        """
        解析等级考试页面
        :return:
        [
            year,
            term,
            exam_name,
            admission_id,
            exam_date,
            final_score,
            listening_score,
            reading_score,
            writing_score,
            other_score
        ]
        """
        doc = BeautifulSoup(content, 'lxml')
        cert_score = []
        trs = doc.find_all('tr')
        for tr in trs[1:]:
            tds = tr.find_all('td')
            score = []
            for td in tds:
                text = td.get_text().strip()
                score.append(text)
            cert_score.append(score)
        return dict(items=cert_score)

    @staticmethod
    def parse_zf_course(content, viewstate, url, cookies, referer):

        course = []

        doc = BeautifulSoup(content, 'lxml')
        xn = doc.find('select').find_all('option')[-1].get_text()

        post_data = {
            '__EVENTTARGET': 'xqd',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            'xnd': xn,
            'xqd': 1
        }

        resp = req(url, 'post', data=post_data, cookies=cookies, referer=referer)
        if resp is None or resp.text is None:
            api.logger.error('[-] got course failed!')
            return {}
        content = resp.text
        doc = BeautifulSoup(content, 'lxml')

        table = doc.find(id='Table1')
        trs = table.find_all('tr')
        for tr in trs[2:]:
            tds = tr.find_all('td')
            for td in tds:
                text = td.get_text(separator=Config.TEXT_SEPARATOR).strip()
                if text != '' and re.match('第\d+节|上午|下午|晚上'.decode('utf-8'), text) is None:
                    l = text.split(Config.TEXT_SEPARATOR)
                    while len(l) < 4:
                        # 有些课程有没有教室的情况
                        l.append('')
                    course.append({
                        'course_name': l[0],
                        'course_time': l[1],
                        'course_teacher': l[2],
                        'course_classroom': l[3]
                    })
        return {xn+'-1': course}

    @staticmethod
    def parse_zf_thesis(content):
        pass


class LibParser(object):

    @staticmethod
    def parse_lib_common(content, tr_start=0, tr_end=9999, td_start=0, td_end=9999):
        """
        通用解析函数，适用于类似:
        ```html
            <table>
                <tr>
                    <td></td>
                    ...
                </tr>
                ...
            </table>
        ```
        的页面解析。

        :param content:  html内容
        :param tr_start: tr起始下标
        :param tr_end:   tr终止下标
        :param td_start: td起始下标
        :param td_end:   td终止下标
        :return:
        """
        doc = BeautifulSoup(content, 'lxml')
        table = doc.find('table')
        res = []
        if table is not None:
            trs = table.find_all('tr')
            for tr in trs[tr_start:tr_end]:
                book = []
                tds = tr.find_all('td')
                for td in tds[td_start:td_end]:
                    text = td.get_text().strip()
                    book.append(text)
                res.append(book)
        return dict(items=res)

    @staticmethod
    def parse_lib_info(content):
        keys = [
            'student_name',
            'student_id',
            'card_no',
            'expire_date',
            'register_date',
            '', '', '', '',
            'student_type',
            '',
            'total_borrow',
            '', 'debt',
            '', 'email',
            'id_num', '', '', '',
            'gender', 'dorm_addr',
            'postcode', 'tel_num', 'cell_num',
            '', '', '', ''
        ]  # '' 为不需要的字段
        res = {}
        doc = BeautifulSoup(content, 'lxml')
        table = doc.find('table')
        tds = table.find_all('td')

        for key, td in zip(keys, tds[1:]):
            if key != '':
                raw = td.get_text(Config.TEXT_SEPARATOR).split(Config.TEXT_SEPARATOR)
                if len(raw) < 2:
                    text = ''
                else:
                    text = raw[1]
                if key == 'total_borrow':
                    r = re.search('\d+', text)
                    text = r.group() if r is not None else ''
                elif key == 'email':
                    r = re.search('[0-9a-zA-Z\.\-_]+@[0-9a-zA-Z\.\-_]+', text)
                    text = r.group() if r is not None else ''
                elif key == 'cell_num' or key == 'tel_num':
                    r = re.search('\d+', text)
                    text = r.group() if r is not None else ''
                res[key] = text
        return res

    @staticmethod
    def parse_lib_curlst(content):
        doc = BeautifulSoup(content, 'lxml')
        table = doc.find('table')
        trs = table.find_all('tr')
        res = []
        for tr in trs[1:]:
            tds = tr.find_all('td')
            book = []
            for td in tds[:-1]:
                if tds.index(td) == 1:
                    text = td.get_text(Config.TEXT_SEPARATOR).split(Config.TEXT_SEPARATOR)[0]
                else:
                    text = td.get_text().strip()
                if text == '':
                    continue
                book.append(text)
            if len(book) > 0:
                res.append(book)
        return dict(items=res)

    @staticmethod
    def parse_lib_shelf(content):
        pass

    @staticmethod
    def parse_lib_comment(content):
        doc = BeautifulSoup(content, 'lxml')
        divs = doc.find_all('div', attrs={'class': 'attitude'})
        res = []
        for div in divs:
            book = []
            ps = div.find_all('p')
            # 书名和作者部分
            text1 = ps[0].get_text(Config.TEXT_SEPARATOR).split(Config.TEXT_SEPARATOR)
            r = re.match('\d+\.(.*)', text1[0])
            text = r.group(1) if r is not None else ''
            book.extend([text.strip(), text1[1].strip()])
            # 评论内容部分
            text2 = ps[1].get_text()
            book.append(text2)
            # 赞与否和发表时间部分
            text3 = ps[2].get_text()
            r = re.search('\((\d+)\).*\((\d+)\).*(\d{4}\-\d{2}\-\d{2}.*)', text3, re.DOTALL)
            up = r.group(1) if r is not None else '0'
            down = r.group(2) if r is not None else '0'
            datetime = r.group(3) if r is not None else '2016-01-01 00:00:00'
            book.extend([up, down, datetime])
            res.append(book)
        return dict(items=res)

    @staticmethod
    def parse_lib_search(content):
        doc = BeautifulSoup(content, 'lxml')
        table = doc.find('table')
        trs = table.find_all('tr')
        res = []
        for tr in trs[1:]:
            book = []
            tds = tr.find_all('td')
            for td in tds[1:]:
                text = td.get_text().strip()
                if tds.index(td) == 1:
                    r = re.search('=(.*)', text)
                    text = r.group(1).strip() if r is not None else ''
                book.append(text)
            res.append(book)
        return dict(items=res)


class EhomeParser(object):

    @staticmethod
    def parse_ehome_info(content):
        username = re.search("var username='(.+)'", content)
        usercode = re.search("var usercode='(\d+)'", content)
        orgname = re.search("var orgname='(.+)'", content)
        cardno = re.search("var cardno='(\d+)'", content)
        typename = re.search("var typename='(.+)'", content)
        current_money = re.search("var currentDBmoney='(.+)'", content)
        username = username.group(1) if username is not None else ''

        # TODO 校园卡号在这里没有正常找到的话，再去图书馆爬虫的INFO字段里面找
        usercode = usercode.group(1) if usercode is not None else ''

        orgname = orgname.group(1) if orgname is not None else ''
        cardno = cardno.group(1) if cardno is not None else ''
        typename = typename.group(1) if typename is not None else ''
        current_money = current_money.group(1) if current_money is not None else ''

        info = dict(username=username,
                    usercode=usercode,
                    orgname=orgname,
                    cardno=cardno,
                    typename=typename,
                    current_money=current_money)
        return info
