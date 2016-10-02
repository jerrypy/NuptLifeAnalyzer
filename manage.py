#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from app import create_app
from flask.ext.script import Manager, Shell

app = create_app(os.getenv('YOUJI_CONFIG') or 'default')
manager = Manager(app)


def make_shell_context():
    return dict(app=app)
manager.add_command("shell", Shell(make_context=make_shell_context))


if __name__ == '__main__':
    manager.run()
