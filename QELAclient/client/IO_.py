from fancytools.os.PathStr import PathStr


hirarchy = ['Module', 'Number', 'Name', 'Current', 'Date']


def pathSplit(path):
    names = PathStr.splitNames(path)
    if len(names) == 4:
        mod = names[0]
        rest = names[3:]
#             print(names)
#             try:

        number, name = names[1].split('__')
        current, date = names[2].split('__')
        date = date.replace('-', ':')
#             except ValueError:
#                 date = names[-2]
#                 number, name = '', ''
#             print(mod, number, name, date, 8888888888888,
#                   names, 555, names[1].split('__'))
        names = [mod, number, name, current, date]
        names.extend(rest)
    return names


def pathJoin(pathlist):
    if len(pathlist) > 5:
        mod, number, name, current, date = pathlist[:5]
        date = date.replace(':', '-')
        dd0 = '__'.join((number, name))
        dd1 = '__'.join((current, date))

        out = PathStr(mod).join(dd0, dd1)
        if len(pathlist[5:]):
            out = out.join(*tuple(pathlist[5:]))
        return out
    return PathStr(pathlist[0]).join(*pathlist[1:])
