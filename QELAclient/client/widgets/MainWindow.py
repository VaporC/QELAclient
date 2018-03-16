import os
import json
from time import sleep
from PyQt5 import QtWidgets, QtGui, QtCore

from fancywidgets.pyQtBased.StatusBar import StatusBar

# LOCAL:
import client

from client.communication import dataArtist
from client.widgets.TabUpload import TabUpload
from client.widgets.TabDownload import TabDownload
from client.widgets.TabConfig import TabConfig
from client.widgets.TabCheck import TabCheck
from client.widgets.CancelProgressBar import CancelProgressBar
from client.widgets.Help import Help
from client.widgets.InlineView import InlineView
# from client.widgets.WebAPI import WebAPI
from client.widgets.Contact import Contact
from client.widgets.Pricing import Pricing
from client.widgets.About import About
from client.widgets.Projects import Projects


class MainWindow(QtWidgets.QMainWindow):
    PATH = client.PATH
    sigMoved = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, server, user, pwd):
        super(). __init__()
        self.user = user
        self.pwd = pwd
        self.server = server

        self.PATH_USER = self.PATH.mkdir(user)
        # TODO: read last root from config
        self.root = self.PATH_USER.mkdir("local")
        self.updateProjectFolder()

        self._lastW = None
        self._about, self._api, self._contact, \
            self.help, self._pricing, self._security = None, None, None, None, None, None

        self.setWindowIcon(QtGui.QIcon(client.ICON))
        self.updateWindowTitle()

        self.resize(1100, 600)

        ll = QtWidgets.QHBoxLayout()
        w = QtWidgets.QWidget()
        w.setLayout(ll)
        self.setCentralWidget(w)

        self.progressbar = CancelProgressBar()
        self.progressbar.hide()

        self.setStatusBar(StatusBar())
        self.statusBar().addPermanentWidget(self.progressbar, stretch=1)

        self.server.sigError.connect(self.statusBar().showError)

#         self.btnMenu = QtWidgets.QPushButton('Menu')
        self.btnMenu = QtWidgets.QPushButton()
        self.btnMenu.setIcon(QtGui.QIcon(
            client.MEDIA_PATH.join('btn_menu.svg')))

        # make button smaller:
        self.btnMenu.setIconSize(QtCore.QSize(20, 20))
#         self.btnMenu.sizeHint = lambda: QtCore.QSize(40, 20)

        self.btnMenu.setFlat(True)
        self._menu = QtWidgets.QMenu()
        a = self._menu.addAction('About QELA')
        a.setToolTip(About.__doc__)
        a.triggered.connect(self._menuShowAbout)
        a = self._menu.addAction('Help')
        a.setToolTip(Help.__doc__)
        a.triggered.connect(self._menuShowHelp)

        a = self._menu.addAction('Change current project')
        a.setToolTip(Projects.__doc__)
        a.triggered.connect(self._menuShowProjects)

        a = self._menu.addAction('Pricing')
        a.setToolTip(Pricing.__doc__)
        a.triggered.connect(self._menuShowPlan)

        a = self._menu.addAction('Website')
        a.setToolTip(
            'Open the application website in your browser')
        a.triggered.connect(self._menuShowWebsite)

        a = self._menu.addAction('Contact')
        a.setToolTip(Contact.__doc__)
        a.triggered.connect(self.menuShowContact)

        self.btnMenu.clicked.connect(self._menuPopup)
        self.btnMenu.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setCornerWidget(self.btnMenu)

        self.help = Help(self)
        self.help.hide()

        self.tabUpload = TabUpload(self)
        self.tabDownload = TabDownload(self)
        self.tabCheck = TabCheck(self)
        self.config = TabConfig(self)
        self.loadConfig()

        self.tabs.addTab(self.config, "Configuration")
        self.tabs.addTab(self.tabUpload, "Upload")
        self.tabs.addTab(self.tabCheck, "Check")
        self.tabs.addTab(self.tabDownload, "Download")

        self.tabCheck.checkUpdates()

        self.tabs.currentChanged.connect(self._activateTab)
        self.tabs.currentChanged.connect(self.help.tabChanged)

        self.tabs.setCurrentIndex(1)

        ll.setContentsMargins(0, 0, 0, 0)

        ll.addWidget(self.tabs)
        ll.addWidget(self.help)

        self._tempBars = []

    def updateProjectFolder(self):

        self._proj = self.server.projectCode()
        self.root.mkdir(self._proj)

    def projectFolder(self):
        return self.root.join(self._proj)

    def _menuShowProjects(self):
        self._projects = Projects(self)
        self._projects.show()

    def loadConfig(self):
        try:
            c = self.server.lastConfig()
            self.config.restore(c)
        except json.decoder.JSONDecodeError:
            print('ERROR loading last config: %s' % c)

    def updateWindowTitle(self, project=None):
        if project is None:
            project = self.server.projectName()
        self.setWindowTitle('QELA | User: %s | Project: %s | Credit: %s' % (
            self.user, project, self.server.remainingCredit()))

    def _menuShowAbout(self):
        if self._about is None:
            self._about = About(self)
        self._about.show()

    def _menuShowHelp(self):
        if self.help.isVisible():
            self.help.hide()
        else:
            self.help.show()

    def _menuShowWebsite(self):
        os.startfile('http://%s' % self.server.address[0])

    def _menuShowPlan(self):
        if self._pricing is None:
            self._pricing = Pricing(self)
        self._pricing.show()

    def menuShowContact(self):
        if self._contact is None:
            self._contact = Contact(self)
        self._contact.show()

    def modules(self):
        '''return a list of all modules either found in imageuploadtable (from client)
        or tabCheck (from server)'''
        ll = list(self.tabCheck.modules())
        ll.extend(self.tabUpload.table.modules())
        return ll

    def openImage(self, path):
        txt = self.config.analysis.cbViewer.currentText()
        if txt == 'dataArtist':
            dataArtist.importFile(path)
        elif txt == 'Inline':
            self._tempview = InlineView(path)
            self._tempview.show()
        else:
            os.startfile(path)

    def _menuPopup(self):
        g = self.btnMenu.geometry()
        p = g.bottomLeft()
        p.setX(p.x() - (self._menu.sizeHint().width() - g.width()))
        self._menu.popup(self.mapToGlobal(p))

#     def _toggleShowHelp(self, checked):
#         if not checked:
#             self.help.hide()
#             self.tabs.setCornerWidget(self.btnMenu)
#             self.btnMenu.show()
#
#         else:
#             self.tabs.setCornerWidget(None)
#             s = self.btnMenu.size()
#             self.help.ltop.addWidget(self.btnMenu, stretch=0)
#
#             self.help.show()
#             self.btnMenu.setFixedSize(s)
#             self.btnMenu.show()

#     def eventFilter(self, _obj, event):
#         if self.help.isVisible():
#             #             if event.type() == QtCore.QEvent.WindowActivate:
#             #                 print("widget window has gained focus")
#             #             elif event.type() == QtCore.QEvent.WindowDeactivate:
#             #                 print("widget window has lost focus")
#             if event.type() == QtCore.QEvent.FocusIn:
#                 print("widget window has lost focus")
#         return False  # event.accept()

    def removeTemporaryProcessBar(self, bar):
        self._tempBars.remove(bar)
        self.statusBar().removeWidget(bar)
        self.progressbar.show()

    def addTemporaryProcessBar(self):
        c = CancelProgressBar()
        self._tempBars.append(c)
        self.progressbar.hide()

#         self.statusBar().removePermanentWidget
        self.statusBar().addPermanentWidget(c, stretch=1)
        return c

    def moveEvent(self, evt):
        self.sigMoved.emit(evt.pos())
#         return QtWidgets.QMainWindow.moveEvent(self, *args, **kwargs)

    def closeEvent(self, ev):
        if not self.server.isReady():
            msg = QtWidgets.QMessageBox()
            msg.setText("You are still uploading/downloading data")
            msg.setStandardButtons(
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
            msg.exec_()
            if msg.result() == QtWidgets.QMessageBox.Ok:
                ev.accept()
            else:
                ev.ignore()
                return
        self.server.logout()
#         self.server.close()
#         sleep(1)
        QtWidgets.QApplication.instance().quit()

    def setTabsEnabled(self, enable=True, exclude=None):
        for i in range(self.tabs.count() - 1):
            if i != exclude:
                self.tabs.setTabEnabled(i, enable)
        if enable:
            self.tabs.setCurrentIndex(2)

    def _activateTab(self, index):
        w = self.tabs.widget(index)
        if self._lastW and hasattr(self._lastW, 'deactivate'):
            self._lastW.deactivate()
        if hasattr(w, 'activate'):
            w.activate()
        self._lastW = w
