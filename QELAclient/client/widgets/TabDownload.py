import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui

from fancytools.os.PathStr import PathStr

# Local:
from client.widgets.FileTableView import FileTableView
from client import IO_


class _DownloadThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(int)
    sigDone = QtCore.pyqtSignal()

    def __init__(self, gui, dfiles, root  # , serverBasePath
                 ):
        super().__init__()
        self.gui = gui
        self._dFiles = dfiles
        self._cancel = False
        self._root = root
#         self.serverBasePath = serverBasePath

    def run(self):
        df = self._dFiles
#         sumsize = sum([f[2] for f in df])
#         s0 = 0
        ll = len(self._dFiles)
        for i, f in enumerate(df):
            #         for i, (f, p, s, fakeFile) in enumerate(df):
            if self._cancel:
                break
#             print(f, self._root, 99999999)
            self.gui.server.download(f, self._root)
#             s0 += s
            self.sigUpdate.emit(int(100 * (i + 1) / ll))
#             continue
#             # remove fake file and parent dir, if empty:
#             fakeFile.remove()
#             f = fakeFile
#             while True:
#                 d = f.dirname()
#                 ll = d.listdir()
#                 if ll or len(d) == len(self.serverBasePath):
#                     break
#                 d.remove()
#                 sleep(0.04)  # wait till file is really removed
#                 f = d
        self.sigDone.emit()

    def kill(self):
        self._cancel = True


class MyFileTableView(FileTableView):
    def __init__(self, gui, fn, fnDownload):
        self.gui = gui
#         self._root = None
        self._filter = None
#         self.updateProject()

        super(). __init__(IO_.hirarchy, fn, fnDownload)

    def pathJoin(self, pathlist):
        return IO_.pathJoin(pathlist)

    def pathSplit(self, path):
        return IO_.pathSplit(path)

    def show(self):
        self.setLocalPath(self.gui.projectFolder())
        self.show = super().show

#         if self._root is None:
#             self._root = self.gui.PATH_USER.mkdir("local")
#             self.setLocalPath(self._root.join(self._proj))
        self.show()

    def rootPathChanged(self, projectChanged=True):
        #         self.gui.root = new_r  # setProjectFolder(new_r)
        self.setLocalPath(self.gui.projectFolder())
        if projectChanged:
            f = self.gui.server.availFiles()
        else:
            f = None
        self.updateServerFiles(f)

#     def rootPath(self):
#         return self._root

#     def updateProject(self):
#         self._proj = self.gui.server.projectCode()

    def setFilter(self, filt):
        if filt == 'Reports only':
            h = [0, 1, 1, 1, 0, 1]
            self._filter = 'report.pdf'
        elif filt == '-':
            h = [0, 0, 0, 0, 0, 0]
            self._filter = None
        elif filt == 'EL images':
            h = [0, 0, 0, 0, 0, 1]
            self._filter = 'EL'
        else:
            raise Exception('Filter type unknown')

        for c, hide in enumerate(h):
            self.setColumnHidden(self.col(c), bool(hide))
        self.update()

    def filter(self, data):
        if self._filter is None:
            return data
        ind = np.char.startswith(data[:, self.col(5)], self._filter)
        return data[ind]


class TabDownload(QtWidgets.QWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        ll = QtWidgets.QHBoxLayout()
        self.setLayout(ll)
        self._dFiles = []

        self._timerFiles = QtCore.QTimer()
        self._timerFiles.setInterval(1000)
        self._timerFiles.timeout.connect(self._checkFiles)
        self._timerFiles.start()
        self.labelLocalPath = QtWidgets.QLabel('Local file path: ')

        leftL = QtWidgets.QVBoxLayout()
        lSyn = QtWidgets.QHBoxLayout()

#         self.labelFiles = QtWidgets.QLabel()

        self.fileTableView = MyFileTableView(
            gui, gui.openImage, self._fnDownload)

        self.btnSync = QtWidgets.QPushButton('Sync All Files')
#         self.btnSync.clicked.connect(lambda: self.currentFileView().sync())
        self.btnSync.clicked.connect(lambda: self.fileTableView.sync())

        self.btnSync.setEnabled(False)

        btnPathChange = QtWidgets.QPushButton('Change')
        btnPathChange.clicked.connect(self._changeRootPath)

        cbFilter = QtWidgets.QComboBox()
        cbFilter.addItems(['-',  'Reports only', 'EL images'])
        cbFilter.currentTextChanged.connect(self.fileTableView.setFilter)
#         self.fileTableView.setFilter(cbFilter.itemText(0))

        lSyn.addWidget(QtWidgets.QLabel('Filter:'))
        lSyn.addWidget(cbFilter)
        lSyn.addStretch()
        lSyn.addWidget(self.labelLocalPath)
        lSyn.addWidget(btnPathChange)
        lSyn.addStretch()

        self.labelFiles = lab = QtWidgets.QLabel()

        lSyn.addWidget(lab)
        lSyn.addWidget(self.btnSync)
        leftL.addLayout(lSyn, stretch=0)
        leftL.addWidget(self.fileTableView, stretch=1)
        ll.addLayout(leftL, stretch=1)

    def _checkFiles(self):
        if not self.isVisible() or not self.gui.server.isReady():
            return
        if self.gui.server.hasNewFiles():
            self.fileTableView.updateServerFiles(self.gui.server.availFiles())
            self.updateStats()

    def updateStats(self):
        (nlocal, nserver, noutdated,
         slocal, sserver, soutdated) = self.fileTableView.stats()

        col0 = self.fileTableView.COL_NOTEXISTANT
        col1 = self.fileTableView.COL_OUTDATED
        self.labelFiles.setText("{} Local ({}) \
<font color='{}'> {} Server ({})  </font> \
<font color='{}'> {} Outdated ({}) </font>".format(nlocal, slocal,
                                                   QtGui.QColor(col0).name(),
                                                   nserver, sserver,
                                                   QtGui.QColor(col1).name(),
                                                   noutdated, soutdated))

        self.btnSync.setEnabled(nserver or noutdated)


#         self.currentFileView().updateServerFiles(self.gui.server.availFiles())

#     def _viewerChanged(self):
#         t = self._btnViewer.text()
#         if t == 'Change to table view':
#             self._btnViewer.setText('Change to tree view')
#             self.fileTreeView.hide()
#             self.fileTableView.show()
#
#         else:
#             self.fileTableView.hide()
#             self.fileTreeView.show()
#             self._btnViewer.setText('Change to table view')
#         self._checkFiles()

    def _fnDownload(self, paths, root, fnDone):
        self._timerFiles.stop()
        b = self.gui.progressbar

        self._t = _DownloadThread(self.gui, paths, root)
        self._t.sigDone.connect(fnDone)
        self._t.sigDone.connect(self._downloadDone)

        self._t.sigUpdate.connect(b.bar.setValue)
        self._t.start()

        b.setColor('darkblue')
        b.bar.setFormat("Downloading images %p%")
        b.setCancel(self._t.kill)
        b.show()

    def _downloadDone(self):
        self._timerFiles.start()
        self.gui.progressbar.hide()
        self.updateStats()

    def _changeRootPath(self):
        r = self.gui.root  # self.fileTableView.rootPath()
        new_r = QtWidgets.QFileDialog.getExistingDirectory(directory=r)
        if new_r:
            self.gui.setProjectFolder(PathStr(new_r))
            self.fileTableView.rootPathChanged(False)  # (PathStr(new_r))
            self._updateFilePathLabel()

    def _updateFilePathLabel(self):
        self.labelLocalPath.setText('Local file path: %s' %
                                    self.gui.root  # self.fileTableView.rootPath()
                                    )

    def activate(self):
        #         if self.isEnabled():
        self.fileTableView.show()
        self._checkFiles()
        self._updateFilePathLabel()

#     def currentFileView(self):
#         if self.fileTableView.isVisible():
#             return self.fileTableView
#         return self.fileTreeView

    #TODO: remove
    def restore(self, *conf):
        # TODO: make use of *conf
        #         self.fileTableView.restore(*conf)
        pass
#         self._updateFilePathLabel()

    def deactivate(self):
        pass
#         self.fileTableView.deactivate()
