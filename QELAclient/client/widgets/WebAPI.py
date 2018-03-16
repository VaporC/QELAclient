from PyQt5 import QtWidgets


class WebAPI(QtWidgets.QTextBrowser):
    def __init__(self, gui):
        super().__init__()
        self.setWindowTitle('WebAPI')
        self.setWindowIcon(gui.windowIcon())
        self.resize(640, self.height())

        self.setHtml(gui.server.api())
