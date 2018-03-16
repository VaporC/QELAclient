from PyQt5 import QtWidgets


class ButtonGroupBox(QtWidgets.QGroupBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.btn = QtWidgets.QPushButton(self)
        self.btn.resize(15, 15)
        self.btn.move(-2, -2)
