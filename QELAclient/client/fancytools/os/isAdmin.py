# -*- coding: utf-8 -*-
from __future__ import print_function
import ctypes
import os


def isAdmin():
    """return True is current os user is administrator"""
    try:
        return os.getuid() == 0
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0


if __name__ == '__main__':
    print("your user is admin: %s" % isAdmin())
