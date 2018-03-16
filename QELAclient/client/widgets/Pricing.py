# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore, QtGui


# TODO: embedd payment in gui - no need for writing mails


def _fillTable(table, data):
    for x, row in enumerate(data):
        for y, cell in enumerate(row):
            item = QtWidgets.QTableWidgetItem()
            item.setText(cell)
            item.setFlags(QtCore.Qt.NoItemFlags | QtCore.Qt.ItemIsEnabled)
#             if cell == '-':
#                 item.setBackground(QtGui.QColor(255, 0, 0, 50))
#             elif cell == 'free':  # ✓':
#                 item.setBackground(QtGui.QColor(0, 255, 0, 50))
            table.setItem(x, y, item)
    font = table.horizontalHeader().font()
    font.setBold(True)
    table.horizontalHeader().setFont(font)

    font = table.verticalHeader().font()
    font.setBold(True)
    table.verticalHeader().setFont(font)
    table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)


def _green(table, x, y):
    table.item(x, y).setBackground(QtGui.QColor(0, 255, 0, 50))


class Pricing(QtWidgets.QWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setWindowTitle('Pricing')
        self.setWindowIcon(gui.windowIcon())

        self.resize(500, 365)

        lay = QtWidgets.QVBoxLayout()
        lay.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(lay)

        lab = QtWidgets.QLabel(
            "Active storage plan: <b>5 GB</b><br><br>For an overview of recent transactions, please refer our invoice send monthly to your email address.<br>\
Charges are either <a href='monthly'>monthly</a> or per <a href='measurement'>measurement</a>.<br>\
To top-up credit balance, please <a href='contact'>contact</a> us.\
<br>An academic discount of 20% can be offered.")
        lab.linkActivated.connect(self._linkClicked)
        lab.linkHovered.connect(self._linkHovered)

        tableMem = QtWidgets.QTableWidget(1, 3)
        tableMem.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        tableMem.setHorizontalHeaderLabels(['5 GB', '50 GB', '500 GB'])
        tableMem.setVerticalHeaderLabels(['Server storage / month           '])

        tableMem.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        tableMem.horizontalHeader().setStretchLastSection(True)

        _fillTable(tableMem, [['free', '10 S$', '50 S$']])
        _green(tableMem, 0, 0)

        tableMem.setFixedHeight(50)

        table = QtWidgets.QTableWidget(8, 2)
        table.verticalHeader().hide()
        table.horizontalHeader().hide()
        table.setColumnWidth(0, 170)

        data = [['free', 'Camera calibration\n'],
                ['', 'Image correction\n'],
                ['pro', 'Image quality and uncertainty\n'],
                ['', 'Image enhancement\n'],
                ['', 'Post processing\n(Cell averages, Cracks etc.)'],
                ['', 'Performance analysis\n(Power + Energy loss)'],
                ['', 'One PDF report for every measurement\n'],
                ['', 'One PDF report for every used camera\n']
                ]
        _fillTable(table, data)
        _green(table, 0, 1)
        _green(table, 1, 1)

        table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        table.resizeRowsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        table.setFixedHeight(330)

        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        lay.addWidget(lab)
        lay.addWidget(tableMem)
        lay.addWidget(table)
        lay.addWidget(QtWidgets.QLabel(
            '<b>  Everything:              1S$ / Image</b>'))
        lay.addStretch()

    def _linkHovered(self, txt):
        tip = None
        if txt == 'measurement':
            tip = '''A measurement is defined as the result of one or multiple electroluminescence images,
taken during ONE continuous process at ONE fixed current'''
        elif txt == 'monthly':
            tip = '''One month is defined as the duration of 30 days from beginning 
of using the service.'''
        if tip:
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tip)
        else:
            QtWidgets.QToolTip.hideText()

    def _linkClicked(self, txt):
        if txt == 'contact':
            self.gui.menuShowContact()


if __name__ == '__main__':
    import sys

    from widgets.Contact import Contact

    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])

    class DummyGui:
        def menuShowContact(self):
            DummyGui.contact = Contact()
            DummyGui.contact.show()

        def windowIcon(self):
            return QtGui.QIcon()

    w = Pricing(DummyGui())

    w.show()
    app.exec_()
