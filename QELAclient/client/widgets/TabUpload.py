import os
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime

from fancytools.os.PathStr import PathStr
# LOCAL
from client.widgets._table import ImageTable, DragWidget


IMG_FILETYPES = ('tiff', 'tif', 'jpg', 'jpeg',
                 'bmp', 'jp2', 'png')


class _UploadThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(bool)
    sigDone = QtCore.pyqtSignal(int)

    def __init__(self, paths, table, server):
        super().__init__()
        self.paths = paths
        self.table = table
        self.server = server

    def run(self):
        for index, p in enumerate(self.paths):
            self.server.upload(p, self.sigUpdate)
            self.sigDone.emit(index)


class TabUpload(QtWidgets.QWidget):
    def __init__(self, gui):
        super().__init__()

        ll = QtWidgets.QVBoxLayout()
        self.setLayout(ll)

        self.gui = gui
        self._tableTempState = ()
        self.setAcceptDrops(True)
        lheader = QtWidgets.QHBoxLayout()

        self.cbMetaData = btn1 = QtWidgets.QCheckBox('Read image meta data')
        self.cbMetaData.setChecked(True)
        self.cbMetaData.setToolTip(
            'Read camera parameters from file meta data / this will slow the import down')

        self.comboAgenda = QtWidgets.QComboBox()
        self.comboAgenda.activated.connect(self._buildAgendas)
        self._buildAgendas()
        self.comboAgenda.currentTextChanged.connect(self._chooseAgenda)

        self.btnUpload = btn3 = QtWidgets.QPushButton('Upload')
        self.btnUpload.setEnabled(False)

        btn3.clicked.connect(self.upload)

        lheader.addWidget(btn1, alignment=QtCore.Qt.AlignLeft, stretch=0)
        lheader.addStretch()
        lheader.addWidget(QtWidgets.QLabel("Agenda: "),
                          alignment=QtCore.Qt.AlignCenter, stretch=0)
        lheader.addWidget(self.comboAgenda,
                          alignment=QtCore.Qt.AlignCenter, stretch=0)
        lheader.addStretch()

        self.labelState = QtWidgets.QLabel()
        lheader.addWidget(
            self.labelState, alignment=QtCore.Qt.AlignRight, stretch=0)

        lheader.addWidget(btn3, alignment=QtCore.Qt.AlignRight, stretch=0)
        ll.addLayout(lheader)

        self._layPath = QtWidgets.QGridLayout()
        ll.addLayout(self._layPath)

        self.lab = QtWidgets.QLabel("""<h1>Drag'N'Drop</h1>one or more Files of Folders<br>Supported image types:<br>%s
<br>Drop a CSV-file to directly import an agenda.""" % str(IMG_FILETYPES)[1:-1])
        ll.addWidget(self.lab, alignment=QtCore.Qt.AlignCenter, stretch=1)
        self.dragW = d = DragWidget()
        self._layPath.addWidget(d)

        self.table = ImageTable(self)
        self.table.filled.connect(self._tableFilled)
        self.table.sigIsEmpty.connect(self._initState)

        ll.addWidget(self.table, stretch=1)

    def _tableFilled(self):
        self.btnUpload.setEnabled(True)
        self.setAcceptDrops(True)

    def _initState(self):
        self.dragW.hide()
        self.table.hide()
        self.lab.show()
        self.setAcceptDrops(True)

    def _chooseAgenda(self, txt):
        if txt:
            self.dragW.show()
            self.table.show()
            self.lab.hide()

            if txt != 'CURRENT':
                self._tableTempState = self.table.saveState()
                path = self.gui.PATH_USER.join('upload', txt + '.csv')
                self.table.fillFromFile(path)
            else:
                if len(self._tableTempState):
                    self.table.fillFromState(self._tableTempState)
                else:
                    self._initState()

    def _buildAgendas(self):
        tt = self.comboAgenda.currentText()
        self.comboAgenda.clear()
        items = ['CURRENT']
        items.extend([f.basename()[:-4] for f in
                      self.gui.PATH_USER.join('upload').files()][::-1])
        self.comboAgenda.addItems(items)
        if tt in items:
            self.comboAgenda.setCurrentText(tt)

    def _checkUploadPossible(self):
        CC = QtWidgets.QMessageBox
        # check whether all cells are filled
#         if not self.table.isVisible():
#             CC.warning(self, "Nothing to upload",
#                                     "It is recommended to fill every cell. Continue?",
#
        if self.table.hasEmptyCells():
            msg = CC.warning(self, "Table has empty cells",
                             "It is recommended to fill every cell. Continue?",
                             QtWidgets.QMessageBox.Ok |
                             QtWidgets.QMessageBox.Cancel)
            if msg == QtWidgets.QMessageBox.Cancel:
                return False
        # TODO:
        if not self.gui.config.checkValid():  # check whether all config info given
            return False

        return True

    def _updateContingentMsg(self):
        if self.gui.server.isReady():
            iused, contingent, memused, memavail = self.gui.server.userPlan()
            self.labelState.setText(
                'Measurements: %s / %s daily    Memory: %s / %s GB' % (
                    iused, contingent, memused, memavail))

    def activate(self):
        self._updateContingentMsg()

    def upload(self):
        if not self._checkUploadPossible():
            return
        self.setAcceptDrops(False)
        self.dragW.setEnabled(False)

        self.btnUpload.setEnabled(False)
        self.btnUpload.clicked.connect(self.cancelUpload)

#             self._p = 'agenda.csv'

        # limit number of upload agendas:
        MAX_AGENDAS = 100
        fol = self.gui.PATH_USER.mkdir('upload')
        files = fol.listdir()
        if len(files) > MAX_AGENDAS:
            for f in files[-MAX_AGENDAS:]:
                fol.join(f).remove()

        plocal = fol.join(
            datetime.now().strftime('%Y-%m-%d__%H-%M-%S.csv'))

        CC = QtWidgets.QMessageBox.critical
        answer = self.gui.server.setConfig(self.gui.config.toStr())
        if answer != 'OK':
            return CC(self, "Could not upload config",
                      answer, QtWidgets.QMessageBox.Ok)

        csvstr = self.table.toCSVStr()
        with open(plocal, 'w') as f:
            f.write(csvstr)
        answer = self.gui.server.setAgenda(csvstr)
        if answer != 'OK':
            return CC(self, "Could not upload agenda ",
                            answer, QtWidgets.QMessageBox.Ok)


#             self._p2 = 'config.json'
#
#             self.gui.config.saveToFile(self._p2)
#             self.table.toCSV(self._p, plocal)
#
#             self.gui.server.upload([self._p, self._p2],
#                                    fnDone=self._uploadStart)

#     def _uploadStart(self):
#         answer = self.gui.server.uploadPossible()
#         if answer != 'OK':
#             self._uploadDone()
#             QtWidgets.QMessageBox.critical(self, "Could not upload images",
#                                            answer, QtWidgets.QMessageBox.Ok)

#         else:
        # TODO:< dont write file to storaye - do all in memory
#         os.remove(self._p)
#         os.remove(self._p2)
        #>

        self.table.insertColumn(0)
        h = QtWidgets.QTableWidgetItem()
        h.setText('Progress')
        b = self.gui.progressbar
        b.setColor('darkred')
        b.setCancel(self.cancelUpload)
        b.show()
        self.gui.server.upload(
            self.table.paths, self.table.new_paths,
            self._uploadUpdate, self._uploadDone)

    def _uploadUpdate(self, index, val):
        bar = self.table.cellWidget(index, 0)
        if not bar:
            bar = QtWidgets.QProgressBar()
            self.table.setCellWidget(index, 0, bar)
            # hide all top rows:
            [self.table.hideRow(i) for i in range(index)]
        bar.setValue(val)

        i, j = index + 1, len(self.table.paths)
        b = self.gui.progressbar
        b.bar.setValue(100 * i / j)
        b.bar.setFormat("Uploading image %i/%i" % (i, j))

    def _uploadDone(self):
        self.setAcceptDrops(True)
        self.dragW.setEnabled(True)
        self.dragW.hide()
        self.table.removeColumn(0)
        self.table.clearContents()

        self.table.hide()
        self.lab.show()
        self._updateContingentMsg()
        self._progressImgs()
        self.gui.updateWindowTitle()

    def _progressImgs(self):
        self.gui.server.uploadDone()
        self._timer = QtCore.QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._updateProgressImages)
        self._timer.start()
        b = self.gui.progressbar
        b.setColor('purple')
        b.setCancel(lambda: self.gui.server.stopProcessing())
        b.show()
        self._updateProgressImages()

    def _updateProgressImages(self):
        if self.gui.server.isReady():
            s = self.gui.server.state()
            b = self.gui.progressbar
            try:
                # extract value from e.g. 'Correct Images 13%'
                i = s[::-1].index(' ')
                val = int(s[-i:-1])
                txt = s[:-i] + '%p%'
                b.bar.setValue(val)
                b.bar.setFormat(txt)
                if val == 100:
                    # processing done
                    self._timer.stop()
                    b.hide()
                    del self._timer
            except ValueError:
                # processing done
                self.gui.statusBar().showMessage(s)

    def cancelUpload(self):
        self.gui.server.cancelUpload()
        self.table.removeColumn(0)

        self.setAcceptDrops(True)
        self.dragW.setEnabled(True)

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Paste):
            self.dropEvent(QtWidgets.QApplication.clipboard())

    def dragEnterEvent(self, event):
        m = event.mimeData()
        if (m.hasUrls()):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def _getFilePathsFromUrls(self, urls):
        '''
        return a list of all file paths in event.mimeData.urls()
        '''
        limg, lagenda = [], []

        def _appendRecursive(path):
            if path.isfile():
                if path.filetype() in IMG_FILETYPES:
                    limg.append(path)
                elif path.filetype() == 'csv':
                    lagenda.append(path)
            else:
                for f in path:
                    # for all files in folder
                    _appendRecursive(path.join(f))
        # one or more files/folders are dropped
        for url in urls:
            if url.isLocalFile():
                path = PathStr(url.toLocalFile())
                if path.exists():
                    _appendRecursive(path)
        return limg, lagenda

    def dropLines(self, lines):
        self.lab.hide()
        self.table.show()
        self.dragW.show()
        self.table.fillFromState(lines, appendRows=True)

    def dropEvent(self, event):
        m = event.mimeData()
        if m.hasUrls():
            self.btnUpload.setEnabled(False)

            pathimgs, pathagendas = self._getFilePathsFromUrls(m.urls())
            if pathimgs or pathagendas:
                self.lab.hide()
                self.table.show()
                self.dragW.show()
            if pathimgs:
                self.setAcceptDrops(False)
#                 self.dragW.setExamplePath(pathimgs[0])
                self.table.fillFromPaths(pathimgs)
            for p in pathagendas:
                self.table.fillFromFile(p, appendRows=True)
            if not pathimgs and pathagendas:
                self.setAcceptDrops(True)
