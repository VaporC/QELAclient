from PyQt5 import QtWidgets, QtGui, QtCore


class InlineView(QtWidgets.QGraphicsView):
    '''
    an image viewer with zoom on mouse wheel
    and context menu
    '''

    def __init__(self, path):
        super().__init__()
        self.scene = QtWidgets.QGraphicsScene()
        self._pm = QtGui.QPixmap(path)
        self.scene.addPixmap(self._pm)
        self.setWindowTitle(path)
        self.setScene(self.scene)
        self._wheel = False
        self._fit(size=QtCore.QSize(640, 800))

    def _fit(self, _checked=None, size=None):
        # fit to window size
        if size is None:
            size = self.size()
        s1 = self._pm.size()
        a0 = size.width() / s1.width()
        a1 = size.height() / s1.height()
        mx = min(a0, a1)
        self.resetTransform()
        self.scale(mx, mx)

    def wheelEvent(self, event):
        event.ignore()
        y = event.angleDelta().y()
        step = 1 + (y / 1440)
        self._wheel = True
        self.scale(step, step)

    def resizeEvent(self, evt):
        if not self._wheel:
            self._fit()
        super().resizeEvent(evt)
        self._wheel = False

    def contextMenuEvent(self, evt):
        menu = QtWidgets.QMenu()
        menu.addAction('Fit Window').triggered.connect(self._fit)
        menu.addAction('Zoom=1').triggered.connect(self.resetTransform)
        menu.exec_(evt.globalPos())


if __name__ == '__main__':
    import sys
    import daServer
    from fancytools.os.PathStr import PathStr

    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])

    d = PathStr(daServer.__file__).dirname().join(
        'MEDIA', 'test.jpg')

    II = InlineView(d)
    II.show()

    app.exec_()
