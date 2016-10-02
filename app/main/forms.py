#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


class ZfLoginForm(Form):
    student_id = StringField(u'学号', validators=[DataRequired()])
    password = PasswordField(u'密码', validators=[DataRequired()])
    captcha = StringField(u'验证码', validators=[DataRequired()])
    submit = SubmitField(u'登录')


class LibLoginForm(Form):
    password = PasswordField(u'图书馆密码', validators=[DataRequired()])


class EhomeLoginForm(Form):
    password = PasswordField(u'智慧校园密码', validators=[DataRequired()])
