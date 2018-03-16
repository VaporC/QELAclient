from PyQt5 import QtWidgets, QtCore, QtGui
Qt = QtCore.Qt


class SnippingArea(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self._mMouseIsDown = False

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setFixedSize(QtWidgets.QApplication.desktop().size())
        self.setCursor(QtGui.QCursor(Qt.CrossCursor))

        self.accepted.connect(self._grabArea)

        app = QtWidgets.QApplication.instance()
        des = QtWidgets.QApplication.desktop()
        self._desk_rect = des.availableGeometry(self)
        screen = app.screens()[des.screenNumber(QtGui.QCursor.pos())]
        size = screen.geometry().size()
        self._desk_rect.setSize(size)

    def mousePressEvent(self, evt):
        if evt.button() != Qt.LeftButton:
            return
        self._mMouseCurPosition = self._mMouseDownPosition = evt.pos()
        self._mMouseIsDown = True

    def mouseReleaseEvent(self, evt):
        if evt.button() != Qt.LeftButton:
            return
        self._mMouseIsDown = False
        self._mCaptureArea
        self.accept()

    def _grabArea(self):
        app = QtWidgets.QApplication.instance()
        des = QtWidgets.QApplication.desktop()
        screen = app.screens()[des.screenNumber(QtGui.QCursor.pos())]

        m = self._mCaptureArea
        m.moveTo(m.topLeft() + screen.geometry().topLeft())

        self.img = screen.grabWindow(
            des.winId(), m.x(), m.y(), m.width(), m.height())

    def mouseMoveEvent(self, evt):
        if not self._mMouseIsDown:
            return
        self._mMouseCurPosition = evt.pos()
        self.update()
        return super().mouseMoveEvent(evt)

    def paintEvent(self, evt):
        p = QtGui.QPainter(self)
        p.setBrush(QtGui.QColor(0, 0, 0, 150))

        if self._mMouseIsDown:
            self._mCaptureArea = self._calculateArea(
                self._mMouseDownPosition, self._mMouseCurPosition)
            p.setClipRegion(QtGui.QRegion(self._desk_rect).subtracted(
                QtGui.QRegion(self._mCaptureArea)))

            p.drawRect(self._desk_rect)
            p.setPen(QtGui.QPen(Qt.red, 4, Qt.SolidLine,
                                Qt.SquareCap, Qt.MiterJoin))
            p.drawRect(self._mCaptureArea)
        else:
            p.drawRect(self._desk_rect)

        return super().paintEvent(evt)

    @staticmethod
    def _calculateArea(pointA, pointB):
        return QtCore.QRect(QtCore.QPoint(pointA.x() if pointA.x()
                                          <= pointB.x() else pointB.x(),
                                          pointA.y() if pointA.y()
                                          <= pointB.y() else pointB.y()),
                            QtCore.QPoint(pointA.x() if pointA.x()
                                          >= pointB.x() else pointB.x(),
                                          pointA.y() if pointA.y()
                                          >= pointB.y() else pointB.y()))


if __name__ == '__main__':
    import sys
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################

    app = QtWidgets.QApplication(sys.argv)

    s = SnippingArea()
    s.exec_()

    lab = QtWidgets.QLabel()
    lab.setPixmap(s.img)
    lab.show()

    app.exec_()
