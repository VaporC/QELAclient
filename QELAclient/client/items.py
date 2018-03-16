from PyQt5 import QtGui, QtCore

# ASCIEXPR = QtCore.QRegExp("[A-Za-z0-9_-]{0,255}")


class FilenamesValidator(QtGui.QRegExpValidator):
    def __init__(self, parent):
        QtGui.QRegExpValidator.__init__(self,
                                        QtCore.QRegExp("[A-Za-z0-9_-]{0,255}"),
                                        parent)

    def validate(self, inp, pos):
        if len(inp) > 255:
            return QtGui.QValidator.Invalid, inp, pos
        return QtGui.QRegExpValidator.validate(self, inp, pos)


# def filenameValidator(self):
#     return IndivFilenamesValidator(self)


# def filenameValidator(self):
#     return QtGui.QRegExpValidator(
#         QtCore.QRegExp("[A-Za-z0-9_-]{0,255}"), self)
#
