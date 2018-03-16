import linecache

# from client import DELIMITER
DELIMITER = ';'


def agendaFromChanged(agendaPath, data):
    lines = []
    rows = data['image indices']
    rows.extend(data['background indices'])
    for row in rows:
        lines.append(linecache.getline(
            agendaPath, row + 1)[:-1].split(DELIMITER))
    return lines
