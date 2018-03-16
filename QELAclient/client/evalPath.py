'''
Created on 28 Feb 2018

@author: serkgb
'''


def _fnNumberAndName(row, index):
    ind = 1
    for ind, c in enumerate(index):
        if not c.isdigit():
            break
    row[1] = index[ind:]  # measurement name
    try:  # meas. number
        row[0] = int(index[:ind])
    except (ValueError, UnboundLocalError):
        row[0] = 1


def _fnCurrent(row, basename):
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


def _fnName(row, s):
    row[2] = s


def _fnTime(row, s):
    row[5] = float(s[:-1])


CAT_FUNCTIONS = {"Meas. number and name [##Name]": _fnNumberAndName,
                 'Current [#A]': _fnCurrent,
                 'Module [Name]': _fnName,
                 'Exposure time [#s]': _fnTime}


def _fnDummy(row, s):
    pass


def evalPath(s):
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
    _DD = {'n': _fnIndex,  # TODO: move to module - so its no eval all the time
           'N': _fnName,
           'i': _fnID,
           'C': _fnCurrent,
           'D': _fnDate,
           't': _fnTime,
           'I': _fnISO,
           'f': _fnFnumber}
    for i, l in enumerate(s):
        if l == '#':
            typ = _DD.get(s[i + 1], _fnDummy)
            if typ == _fnDate:
                istart = i + 2
                iend = s[i + 2:].index('}') + istart
                format = s[istart:iend]
                # TODO: split string
                _fnDate()


if __name__ == '__main__':
    evalPath('#n__#nlkj:#t_kjh#f.png')
