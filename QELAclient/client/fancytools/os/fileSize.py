'''
Created on 1 Aug 2017

@author: serkgb
'''
import math
size_name = (" B", " KB", " MB", " GB", " TB", " PB", " EB", " ZB", " YB")


def toStr(size_bytes):
    if size_bytes == 0:
        return "0 B"
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s%s" % (s, size_name[i])


def toBytes(size_str):
    for i, s in enumerate(size_name):
        if s in size_str:
            break
    return float(size_str[:len(s)]) * math.pow(1024, i)


if __name__ == '__main__':
    s = 167576551576
    ss = toStr(s)
    sss = toBytes(ss)
    print(s, ss, sss)
