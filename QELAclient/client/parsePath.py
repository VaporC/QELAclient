import re
from datetime import datetime


def _numberAndName(row, index):
    ind = 1
    for ind, c in enumerate(index):
        if not c.isdigit():
            break
    row[1] = index[ind:]  # measurement name
    try:  # meas. number
        row[0] = int(index[:ind])
    except (ValueError, UnboundLocalError):
        row[0] = 1


def _current(row, basename):
    try:
        end = basename.index('A')
        for i in range(end - 1, -1, -1):
            if not basename[i].isdigit() and basename[i] != '-':
                break
        rr = basename[i:end].replace('-', '.')

        row[3] = float(rr)
    except Exception:
        # background?
        row[3] = 0


def _name(row, s):
    row[2] = s


def _time(row, s):
    row[5] = _float(s)


CAT_FUNCTIONS = {"Meas. number and name [##Name]": _numberAndName,
                 'Current [#A]': _current,
                 'Module [Name]': _name,
                 'Exposure time [#s]': _time}


# format functions:
def _onlyDigits(s):
    s = re.sub('[^\d\.]', "", s)  # filter digits and dots
    if s[-1] == '.':
        s = s[:-1]
    return s


def _int(s):
    return int(_onlyDigits(s))


def _float(s):
    return float(_onlyDigits(s))


def _pass(s):
    return s


def _date(style, s):
    return datetime.strptime(s, style).strftime('%x %X')


# format function TabUpload table columns
_DD = {'n': _int,  # meas number
       'N': _pass,  # meas name
       'i': _pass,  # ID
       'C': _float,  # current
       'D': _date,  # date
       't': _float,  # exposure time
       'I': _float,  # iso
       'f': _float}  # fnumber

# column index in TabUpload table:
_RR = {'n': 0,  # meas number
       'N': 1,  # meas name
       'i': 2,  # ID
       'C': 3,  # current
       'D': 4,  # date
       't': 5,  # exposure time
       'I': 6,  # iso
       'f': 7}


def toRow(row, d):
    for k, v in d.items():
        row[_RR[k]] = v


def parsePath(path, style):
    '''
    Extract values such as ISO, exposure time etc from directory of file name.
    Values to be extracted are indicated with a leading '%' followed be a value code:
    #n --> Measurement index 
    #N --> Measurement name
    #i --> Module ID
    #C --> Current [A]
    #D{...} --> Date, format following https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
              example:
              #D{%Y-%m-%d_%H:%M} --> 2018-12-02_15:34
    #t --> exposure time [s]
    #I --> ISO
    #f --> f-number
    '''
    out = {}  # X:val
    while True:
        try:
            # start index
            i0 = style.index('#')
            j0 = i0
        except ValueError:
            break

        styp = style[i0 + 1]  # n,N,T...

        typ = _DD.get(styp, _pass)  # _float, _int...

        if typ == _date:  # extract datetype the str between {}
            i = i0 + 2
            iend = style[i + 2:].index('}') + i
            datetype = style[i + 1:iend + 2]
            i0 = iend + 1

        try:  # stop index
            nextletter = style[i0 + 2]
            i1 = i0 + 2
            j1 = j0 + path[j0:].index(nextletter, None)
        except (ValueError, IndexError):
            i1, j1 = None, None

        # get value
        sval = path[j0:j1]
        if typ == _date:
            val = _date(datetype, sval)
        else:
            val = typ(sval)
        out[styp] = val
        if i1 is None:
            break
        # shorten style and path:
        path = path[j1:]
        style = style[i1:]

    return out


if __name__ == '__main__':
    D = [(r'03rd Round',
          '0#nrd #N',
          {'n': 3, 'N': 'Round'}),
         (r'12__33_AA-2.3_XXX_2015-02-24T13:00:00.png',
          '#n__#t_AA-#f_XXX_#D{%Y-%m-%dT%H:%M:%S}.png',
          {'n': 12, 't': 33.0, 'f': 2.3, 'D': '02/24/15 13:00:00'})]

    for path, style, answer in D:
        assert parsePath(path, style) == answer
