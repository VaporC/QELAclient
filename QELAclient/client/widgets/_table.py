from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime
import numpy as np


from fancytools.utils import json2 as json
from fancytools.os.PathStr import PathStr

from imgProcessor.utils.metaData import metaData


# local
from client.widgets.GridEditor import GridEditorDialog
from client.parsePath import CAT_FUNCTIONS, parsePath, toRow

MATRIX_HEADER = ['Path', "Measurement Index", "M. name",
                 "Module ID", 'Current [A]',  # 'I. number',
                 'Date', 'Exposure time [s]', 'ISO(Gain)', 'f-number', 'Options']
MATRIX_HEADER_WIDTH = [335, 120, 57, 80, 70, 130, 104, 64, 62]

DELIMITER = ';'

# CATEGORIES = (
#     (True, "Meas. number and name [##Name]", "Date"),  # Measurement
#     (True, 'Current [#A]'),  # Current
#     (True, 'Module [Name]',),  # ID
#     #     ('Exposure time [_e#.file]',),  # exposure time ##TODO
#     (False, 'Exposure time [#s]',),  # exposure time
# )


# DELIMITER = ',\t'


# def argmin(l):
#     '''numpy-free version of argmin'''
#     mindist = min(l)
#     for i, d in enumerate(l):
#         if d == mindist:
#             break
#     return i


class _OnlyIntDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        le = QtWidgets.QLineEdit(parent)
        v = QtGui.QIntValidator(0, 10000, le)
        le.setValidator(v)
        return le


class _OnlyNumberDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        le = QtWidgets.QLineEdit(parent)
        v = QtGui.QDoubleValidator(0., 100000., 6)
        le.setValidator(v)
        return le


class _OnlyDateDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        le = QtWidgets.QDateTimeEdit(QtCore.QDate.currentDate(), parent)
        le.setDisplayFormat("yyyy.MM.dd HH:mm:ss")
        return le


class _TableBase(QtWidgets.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.horizontalHeader().setStretchLastSection(True)
        self.cellDoubleClicked.connect(self._cellDoubleClicked)
        self.currentCellChanged.connect(self._showPreview)

    def _applyForAll(self):
        txt = self.currentItem().text()
        col = self.currentColumn()
        for row in range(self.rowCount()):
            self.item(row, col).setText(txt)

    def keyPressEvent(self, evt):
        if evt.matches(QtGui.QKeySequence.Delete):
            for ran in self.selectedRanges():
                for row in range(ran.bottomRow(), ran.topRow() - 1, -1):
                    self.removeRow(row)
        elif evt.matches(QtGui.QKeySequence.SelectAll):
            self.selectAll()
        elif evt.matches(QtGui.QKeySequence.Copy):
            self.copyToClipboard()
        else:
            super().keyPressEvent(evt)

    def copyToClipboard(self, cellrange=None):
        if cellrange is None:
            cellrange = self.selectedRanges()[0]
        # deselect all other ranges, to show shat only the first one will
        # copied
        for otherRange in self.selectedRanges()[1:]:
            self.setRangeSelected(otherRange, False)
        nCols = cellrange.columnCount()
        nRows = cellrange.rowCount()
        if not nCols or not nRows:
            return
        text = ''
        lastRow = nRows + cellrange.topRow()
        lastCol = nCols + cellrange.leftColumn()
        for row in range(cellrange.topRow(), lastRow):
            for col in range(cellrange.leftColumn(), lastCol):
                item = self.item(row, col)
                if item:
                    text += str(item.text())
                if col != lastCol - 1:
                    text += '\t'
            text += '\n'
        QtWidgets.QApplication.clipboard().setText(text)

    def removeRow(self, row):
        self.paths.pop(row)
        super().removeRow(row)
        if not len(self.paths):
            self.sigIsEmpty.emit()

    def clearContents(self):
        for row in range(len(self.paths) - 1, -1, -1):
            super().removeRow(row)
        self.paths = []

    def saveState(self):
        rows = []
        for row in range(self.rowCount()):
            line = []
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    line.append(str(item.text()))
                else:
                    line.append(None)
            rows.append(line)
        return rows

    def _closePreview(self):
        try:
            self._tempIconWindow.close()
            del self._tempIconWindow
            self.gui.sigMoved.disconnect(self._prefWinFn)
            self.gui.tabs.currentChanged.disconnect(self._closePreview)
        except AttributeError:
            pass

    def wheelEvent(self, evt):
        '''
        close preview image when mouse wheel is used
        '''
        try:
            self._tempIconWindow.close()
        except AttributeError:
            pass
        super().wheelEvent(evt)

    def _doShowPreview(self, path, row, pixmap):

        if pixmap and row == self.currentRow():
            lab = self._tempIconWindow = QtWidgets.QLabel()

            lab.mouseDoubleClickEvent = lambda _evt, path=path: \
                self.gui.openImage(path)

            lab.setPixmap(pixmap)
            lab.setWindowFlags(QtCore.Qt.FramelessWindowHint
                               | QtCore.Qt.SubWindow
                               )
            lab.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            p0 = self.mapToGlobal(self.parent().pos())

            p1 = QtCore.QPoint(- pixmap.size().width(),
                               self.rowViewportPosition(self._Lrow))
#                 del self._Lrow

            self._prefWinFn = lambda p, p1=p1: lab.move(
                p + p1 + self.mapTo(self.gui, self.parent().pos()))
            self.gui.sigMoved.connect(self._prefWinFn)
            self.gui.tabs.currentChanged.connect(self._closePreview)

            lab.move(p0 + p1)

            # if the context menu is vsibile before (right clicked on a row
            # then showing preview will hide it again
            # we dont want this - we make menu visibe afterwards
            try:
                menu_visible = self._menu.isVisible()
            except AttributeError:
                menu_visible = False

            lab.show()

            if menu_visible:
                self._menu.setVisible(True)

    def _showPreview(self, row, col):
        self._closePreview()
        # show an image preview
        if col == 0:
            path = self.item(row, col).text()
            self._Lrow = row
            # load image in thread to not block GUI:
            self._L = _LoadPreviewThread(path, row)
            self._L.sigDone.connect(self._doShowPreview)
            self._L.start()

    def _cellDoubleClicked(self, row, col):
        if col == 0:
            path = self.item(row, col).text()
            self.gui.openImage(path)


# class CRFTable(_TableBase):
#     # camera response function upload
#     def __init__(self):
#         super().__init__(1, 2)  # int rows, int columns


class ImageTable(_TableBase):
    filled = QtCore.pyqtSignal(bool)  # success
    sigIsEmpty = QtCore.pyqtSignal()

    def __init__(self, imgTab):
        super().__init__(1, len(MATRIX_HEADER))  # int rows, int columns
        self.setTextElideMode(QtCore.Qt.ElideLeft)

        # draw top header frame :
        header = self.horizontalHeader()
        header.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        header.setLineWidth(1)
        self.setHorizontalHeader(header)

        [self.setColumnWidth(n, width)
         for n, width in enumerate(MATRIX_HEADER_WIDTH)]
        self._showOptionsColumn(False)

        self.cbMetaData = imgTab.cbMetaData
        self.gui = imgTab.gui
        self.drawWidget = imgTab.dragW

        self.setHorizontalHeaderLabels(MATRIX_HEADER)
        self.drawWidget.changed.connect(self.valsFromPath)
        self.filled.connect(self.valsFromPath)

        self.paths = []

        # need to add to self, otherwise garbage collector removes delegates
        self._delegates = {1: _OnlyIntDelegate(),  # measurement number
                           4: _OnlyNumberDelegate(),  # current
                           5: _OnlyDateDelegate(),  # date
                           6: _OnlyNumberDelegate(),  # exp time
                           7: _OnlyNumberDelegate(),  # iso
                           8: _OnlyNumberDelegate()}  # fnumber

        for i, d in self._delegates.items():
            self.setItemDelegateForColumn(i, d)

        self.hide()
        self.setRowCount(0)

    def hasEmptyCells(self, select=True) -> bool:
        '''
        returns whether table contains empty cells

        if <select> == True: select all empty cells
        '''
        has_empty = False
        for row in range(self.rowCount()):
            if not self.isRowHidden(row):
                for col in range(1, self.columnCount()):
                    if not self.isColumnHidden(col):
                        item = self.item(row, col)
                        if not item or not item.text():
                            if not select:
                                return True
                            has_empty = True
                            index = self.model().index(row, col)
                            self.selectionModel().select(index,
                                                         QtCore.QItemSelectionModel.Select)
        return has_empty

    def modules(self):
        '''
        return list of module IDs within table
        '''
        ll = set()
        for row in range(self.rowCount()):
            item = self.item(row, 3)
            if item is not None:
                ll.add(item.text())
        return ll

    def mousePressEvent(self, event):
        mouseBtn = event.button()
        if mouseBtn == QtCore.Qt.RightButton:
            self._menu = QtWidgets.QMenu()
            self._menu.addAction(
                "Manual grid detection").triggered.connect(self._manualGridDetection)
            self._menu.addAction("Apply for all").triggered.connect(
                self._applyForAll)

            self._menu.addAction("Remove row"
                                 ).triggered.connect(lambda: self.removeRow(self.currentRow()))
            self._menu.addAction("Select all"
                                 ).triggered.connect(self.selectAll)

            self._menu.popup(event.globalPos())
        super().mousePressEvent(event)

    def _manualGridDetection(self):
        row = self.currentRow()

        self._gridEditor = g = GridEditorDialog(self.paths[row])
        # move:
        p0 = self.mapToGlobal(self.parent().pos())
        p0.setY(p0.y() + self.rowViewportPosition(row + 1))
        p0.setX(p0.x() + self.columnViewportPosition(2))
        g.move(p0)

        g.exec_()

        if g.result() == g.Accepted:
            row = self.currentRow()
            col = len(MATRIX_HEADER) - 1
            self.setCell(row, col, json.dumps(g.values))
            self._showOptionsColumn(True)

    def toCSVStr(self):
        # TODO generate somewhere else - shoudl also work when toCSV not
        # executed
        #         self.new_paths = []

        #         with open(path, 'w') as f:
        #             with open(pathlocal, 'w') as flocal:
        out = ''
        for row in range(self.rowCount()):
            # only same image index and ftype to protect the clients
            # data"
            path = self.paths[row]
            new_path = '%i.%s' % (row, path.filetype())
#             self.new_paths.append(new_path)

            rowl = [new_path]
            for col in range(1, self.columnCount()):
                item = self.item(row, col)
                if item:
                    rowl.append(str(item.text()))
            rowl.append(str(path.size()))
            line = DELIMITER.join(rowl)
            if line[-1] != '\n':
                line += '\n'
            out += line
        return line

    # TODO: remove - not needed
#     def toCSV(self, path, pathlocal):
#         # TODO generate somewhere else - shoudl also work when toCSV not
#         # executed
#         self.new_paths = []
#
#         with open(path, 'w') as f:
#             with open(pathlocal, 'w') as flocal:
#                 for row in range(self.rowCount()):
#                     # only same image index and ftype to protect the clients
#                     # data"
#                     path = self.paths[row]
#                     new_path = '%i.%s' % (row, path.filetype())
#                     self.new_paths.append(new_path)
#
#                     rowl = []
#                     for col in range(1, self.columnCount()):
#                         item = self.item(row, col)
#                         if item:
#                             rowl.append(str(item.text()))
#                     rowl.append(str(path.size()))
#                     line = DELIMITER.join(rowl)
#                     if line[-1] != '\n':
#                         line += '\n'
#                     f.write(new_path + DELIMITER + line)
#                     flocal.write(path + DELIMITER + line)

    def fillFromFile(self, path, appendRows=False):
        with open(path, 'r') as f:
            lines = [line.split(DELIMITER)
                     for line in f.readlines()]
        return self.fillFromState(lines, appendRows)

    def fillFromState(self, lines, appendRows=False):
        if appendRows:
            row0 = self.rowCount()
        else:
            row0 = 0
            self.clearContents()
            self.paths = []
        nrows = row0 + len(lines)
        self.setRowCount(nrows)
        for row, line in enumerate(lines):
            row += row0
            for col, txt in enumerate(line):
                if txt:
                    self.setCell(row, col, txt)
            item = self.item(row, 0)
            if len(line) and item:
                self.paths.append(PathStr(item.text()))
                self._setPathItem(row)

            else:
                nrows -= 1
        self.drawWidget.setExamplePath(self.paths[0])
        self.setRowCount(nrows)
        self._checkShowOptionsColumn()

        self.filled.emit(True)

    def _checkShowOptionsColumn(self):
        hasOptions = False
        c = len(MATRIX_HEADER) - 1
        for row in range(self.rowCount()):
            item = self.item(row, c)
            if item and item.text():
                # TODO: this check is only needed because csv reading incl.
                # last sign currently. remove
                if item.text() != '\n':
                    hasOptions = True
                    break
        self._showOptionsColumn(hasOptions)

    def _showOptionsColumn(self, show):
        c = len(MATRIX_HEADER) - 1
        if show:
            # make sure whole options column is readonly:
            for row in range(self.rowCount()):
                item = self.setCell(row, c)
                self.mkItemReadonly(item)
        self.setColumnHidden(c, not show)  # show/hide options

    def fillFromPaths(self, paths):
        self.show()
        self._new_paths = paths
        row0 = len(self.paths)
        self.setRowCount(len(paths) + row0)

        self.drawWidget.setExamplePath(paths[0])

        # <<<
        # adds ...
        # - path to FIRST ROWfile
        # - change date
        # row index

        offs = len(self.paths)
        self._new_rows = []
#         colDate = MATRIX_HEADER.index('Date')
        for r, p in enumerate(self._new_paths):
            if p in self.paths:
                continue  # duplicate found - ignore
            row = r + offs
            # path[column 0] as read-only and underlined:
            self.paths.append(p)
            self._setPathItem(row, p)

            # for colored row indices:
            rowitem = QtWidgets.QTableWidgetItem()
            # previous row item number:
            if row == 0:
                prev = 0
            else:
                item = self.verticalHeaderItem(row - 1)
                if item:
                    prev = int(item.text())
                else:
                    prev = row - 1
            rowitem.setText(str(prev + 1))
            self.setVerticalHeaderItem(row, rowitem)
            self._new_rows.append(row)

        # >>>
#         # correct row count:
#         self.setRowCount(len(self.paths))

#         self.valsFromPath(row0 - 1)
        if self.cbMetaData.isChecked():
            self.addMetaData()
        else:
            self.filled.emit(self.isVisible())

    def isEmpty(self):
        return len(self.paths) == 0

    def valsFromPath(self):  # , row0=-1
        ncol = self.columnCount() - 1  # ignore the options column
        for row in range(self.rowCount()):  # range(row0 + 1, self.rowCount()) # row0=-1
            p = self.item(row, 0).text()
            success, entries = self.drawWidget.model(p)
#             continue
            for col, e in enumerate(entries):
                col += 1
                if e == '':
                    item = self.item(row, col)
                    if hasattr(item, 'metaText'):
                        e = self.item(row, col).metaText

                self.setCell(row, col, str(e))

            # color row index number:
            # check if whole row contains data:
            if '' not in (self.item(row, c).text() for c in range(ncol)):
                color = QtCore.Qt.darkGreen
            elif success:
                color = QtCore.Qt.darkYellow
            else:
                color = QtCore.Qt.red
            rowitem = self.verticalHeaderItem(row)
            rowitem.setForeground(color)
            self.setVerticalHeaderItem(row, rowitem)

    def setCell(self, row, col, txt=None):
        item = self.item(row, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
        if txt is not None:
            item.setText(txt)
        self.setItem(row, col, item)

        return item

    def mkItemReadonly(self, item):
        flags = item.flags()
        flags |= QtCore.Qt.ItemIsSelectable
        flags &= ~QtCore.Qt.ItemIsEditable  # reset/clear the flag
        item.setFlags(flags)

    def _setPathItem(self, row, path=None):
        item = self.setCell(row, 0, path)
        item.setTextAlignment(QtCore.Qt.AlignRight)
        self.mkItemReadonly(item)
        f = item.font()
        f.setUnderline(True)
        item.setFont(f)

#     def fill(self):  # TODO: rename
#         '''
#         adds ...
#         - path to FIRST ROWfile
#         - change date
#         - row index
#         '''
#                            # self.dragW.setExamplePath(pathimgs[0])
#
#         offs = len(self.paths)
#         self._new_rows = []
# #         colDate = MATRIX_HEADER.index('Date')
#         for r, p in enumerate(self._new_paths):
#             if p in self.paths:
#                 continue  # duplicate found - ignore
# #                 # override, if duplicate path found
# #                 row = self.paths.index(p)
# #             else:
#             row = r + offs
#             # path[column 0] as read-only and underlined:
#             self.paths.append(p)
#             self._setPathItem(row, p)
#
#             # add file modification date (might be overridden later by
#             # metadata-data):
#
# #             self.setCell(row, colDate, datetime.fromtimestamp(
# #                 p.date()).strftime('%Y:%m:%d %H:%M:%S'))
# #             itemdate = QtWidgets.QTableWidgetItem()
# #             datestr = datetime.fromtimestamp(
# #                 p.date()).strftime('%Y:%m:%d %H:%M:%S')
# #             itemdate.setText(datestr)
# #             self.setItem(row, MATRIX_HEADER.index('Date'), itemdate)
#
#             # for coloured row indices:
#             rowitem = QtWidgets.QTableWidgetItem()
#             # previous row item number:
#             if row == 0:
#                 prev = 0
#             else:
#                 item = self.verticalHeaderItem(row - 1)
#                 if item:
#                     prev = int(item.text())
#                 else:
#                     prev = row - 1
#
#             rowitem.setText(str(prev + 1))
#
#             self.setVerticalHeaderItem(row, rowitem)
#
#             self._new_rows.append(row)
#
#         # correct row count:
#         self.setRowCount(len(self.paths))

    def addMetaData(self):
        self._thread = _ProcessThread(self._new_rows, self._new_paths)
        self._thread.rowDone.connect(self._fillRow)
        self._thread.finished.connect(self._fillFinished)

        self._b = self.gui.addTemporaryProcessBar()
        self._b.setColor('darkgreen')
        self._b.setCancel(self._thread.kill)
        self._b.show()

        self._thread.start()

    def _fillRow(self, progress, row, meta):
        b = self._b
        b.bar.setValue(progress)
        b.bar.setFormat(
            "Reading image meta data %s" % int(progress) + '%')
        for i, t in enumerate(meta):
            item = self.setCell(row, 5 + i, t)
            item.metaText = t

    def _fillFinished(self):
        self.gui.removeTemporaryProcessBar(self._b)
        self.filled.emit(self.isVisible())


class DragWidget(QtWidgets.QGroupBox):
    '''
    HEADER: fields:[opt1,opt2...]
    row1: PATH      / TO       / FIRST / FILE.XYZ
    row2: [label1],  [label2] <-- drag-able
    '''
    changed = QtCore.pyqtSignal()
    N_LAST_FOLDERS = 5

    def __init__(self):
        super(). __init__('Analyze file path...')
        self.setAcceptDrops(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Maximum)
        self.hide()

        l0 = QtWidgets.QHBoxLayout()
        self.setLayout(l0)

        lleft = QtWidgets.QVBoxLayout()
        lright = QtWidgets.QVBoxLayout()

        l0.addLayout(lleft, stretch=0)
        l0.addLayout(lright, stretch=1)

#         lleft.addWidget(QtWidgets.QLabel("Path contains:    "))
        lleft.addWidget(QtWidgets.QLabel("Example path:"))

        btn = QtWidgets.QPushButton("Blocks:")
        menu = QtWidgets.QMenu()
        menu.setToolTipsVisible(True)

        a = menu.addAction('<INDIVIDUAL>')
        a.setToolTip(parsePath.__doc__)
        a.triggered.connect(self._addParsePathLabel)

        for k in CAT_FUNCTIONS.keys():
            a = menu.addAction(k)
            a.triggered.connect(lambda _checked, k=k:
                                self._addLabel(_RemovableLabel(self._lGrid, k)))
        btn.setMenu(menu)

        lleft.addWidget(btn)  # QtWidgets.QLabel("Blocks:"))
#         lleft.addStretch(1)
#         #<<<<<FILL HEADER WITH FIELD OPTIONS
#         ltop = QtWidgets.QHBoxLayout()
#         lright.addLayout(ltop)
#
#         self.fieldOptions, self.fieldNames = [], []
#         for opts in CATEGORIES:
#             fieldName = QtWidgets.QCheckBox()
#             fieldOptions = QtWidgets.QComboBox(self)
#
#             fieldName.setChecked(opts[0])
#             fieldOptions.setEnabled(opts[0])
#             fieldOptions.addItems(opts[1:])
#
#             ltop.addWidget(fieldName)
#             ltop.addWidget(fieldOptions)
#
#             fieldName.clicked.connect(fieldOptions.setEnabled)
#             fieldOptions.currentIndexChanged.connect(self.changed.emit)
#             fieldName.clicked.connect(self.changed.emit)
#
#             self.fieldOptions.append(fieldOptions)
#             self.fieldNames.append(fieldName)
# #         btnDummy = QtWidgets.QPushButton("Extract values by text")
# #         btnDummy.setToolTip(parsePath.__doc__)
# #         btnDummy.clicked.connect(self._addParsePathLabel)
# #         ltop.addWidget(btnDummy)
#
#         ltop.addStretch(1)
#         #>>>>>>

        ll = self._lGrid = QtWidgets.QGridLayout()
        lright.addLayout(self._lGrid)
        lright.addStretch(1)
        for i in range(self.N_LAST_FOLDERS):

            sep = QtWidgets.QLabel(self)
            sep.setText('/')
            sep.setEnabled(False)
            ll.addWidget(sep, 0, 2 * i)

            lab = QtWidgets.QLabel(self)
            # lab.setText('')
            lab.setEnabled(False)

            ll.addWidget(lab, 0, (2 * i) + 1)

#         for i, (co, ch) in enumerate(zip(self.fieldOptions, self.fieldNames)):
#             lab = _RemovableLabel(self._lGrid, co.currentText())
# #             lab.setText(co.currentText())
#             co.currentIndexChanged.connect(
#                 lambda _index, co=co, lab=lab: lab.setText(co.currentText()))
#             ch.clicked.connect(lambda checked, lab=lab:
#                                self._addRemoveLabel(checked, lab))
#
# #             lab.setFrameStyle(QtWidgets.QFrame.Sunken |
# #                               QtWidgets.QFrame.StyledPanel)
#             p = (2 * i) + 1
#             ll.addWidget(lab, 1, p)
#
#             if not ch.isChecked():
#                 self._addRemoveLabel(False, lab)

    def _addParsePathLabel(self):
        lab = _LabelParsePath(self._lGrid, "#N_#n_")
        lab.setToolTip(parsePath.__doc__)
        lab._editor.setToolTip(parsePath.__doc__)
        lab._editor.editingFinished.connect(self.changed.emit)
        self._addLabel(lab)

    def setExamplePath(self, path):
        #         self.show()
        for i, fold in enumerate(path.splitNames()[-self.N_LAST_FOLDERS:]):
            w = self._lGrid.itemAtPosition(0, 2 * i + 1).widget()
            w.setText(fold)

    def _addLabel(self, label):
        ll = self._lGrid
#         if not checked:
#             ll.removeWidget(label)
#             label.hide()
#         else:
        # find empty space:
        for i in range(ll.columnCount() // 2):
            if not ll.itemAtPosition(1, 2 * i + 1):
                ll.addWidget(label, 1, 2 * i + 1)
                label.show()
                break
        self.changed.emit()

    def activeLabels(self):
        labels = [self._lGrid.itemAtPosition(1, col)
                  for col in range(self._lGrid.columnCount())]
        return [item.widget() for item in labels if item]

    def mousePressEvent(self, event):

        child = self.childAt(event.pos())
        if not child or child not in self.activeLabels():
            self._curChild = None
            return

        self._offs = event.pos().x() - child.pos().x()

        self._curChild = child

        # calc label gap positions:
        la = self._lGrid
        self._poss = []
        for i in range(la.columnCount() // 2):
            lab = la.itemAtPosition(0, 2 * i + 1)
            self._poss.append(lab.geometry().right())

        event.accept()

    def mouseMoveEvent(self, event):
        if not self._curChild:
            return
        # move only in x
        y = self._curChild.pos().y()
        self._curChild.move(event.pos().x() - self._offs, y)

    def labelIndex(self, label):
        return self._lGrid.getItemPosition(
            self._lGrid.indexOf(label))[1]

    def mouseReleaseEvent(self, event):
        if not self._curChild:
            return
        pos = event.pos().x() + self._curChild.rect().center().x()
        i = np.argmin([abs(p - pos) for p in self._poss])
        #
        pos = (2 * i) + 1

        item = self._lGrid.itemAtPosition(1, pos)

        ind = self.labelIndex(self._curChild)
        if item:
            # swap position
            self._lGrid.addWidget(item.widget(), 1, ind)

        self._lGrid.addWidget(self._curChild, 1, pos)
        self._lGrid.update()

        if ind != pos:
            self.changed.emit()

    def model(self, path):
        '''
        depending on adjusted label positions,
        split given path into MATRIX row
        '''
        path = PathStr(path)
        names = path.splitNames()[-self.N_LAST_FOLDERS:]
        names[-1] = PathStr(names[-1]).rmFileType()

        out = [''] * (len(MATRIX_HEADER) - 1)
        success = True
        for i, n in enumerate(names):
            item = self._lGrid.itemAtPosition(1, (2 * i) + 1)
            if item:
                txt = item.widget().text()
                try:
                    fn = CAT_FUNCTIONS[txt]
                    fn(out, n)
                except KeyError:
                    toRow(out, parsePath(n, txt))
#                     print(e)
#                     success = False

        colDate = MATRIX_HEADER.index('Date') - 1
        if not out[colDate]:
            out[colDate] = datetime.fromtimestamp(
                path.date()).strftime('%Y:%m:%d %H:%M:%S')

        return success, out


class _RemovableLabel(QtWidgets.QLabel):
    def __init__(self, layout, txt):
        super(). __init__(txt)
        self._lay = layout
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

        self.setFrameStyle(QtWidgets.QFrame.Sunken |
                           QtWidgets.QFrame.StyledPanel)

    def remove(self):
        self._lay.removeWidget(self)
        self.close()

    def showMenu(self, evt):
        m = QtWidgets.QMenu()
        m.addAction('Remove').triggered.connect(self.remove)
        m.exec_(self.mapToGlobal(evt))


class _LabelParsePath(_RemovableLabel):
    '''
    Dummy placeholder label within dragWidget
    Can be modified at double click
    remove option is shown at right click
    '''

    def __init__(self, layout, txt):
        super(). __init__(layout, txt)

        p = self.palette()
        p.setColor(QtGui.QPalette.WindowText, QtGui.QColor('gray'))
        self.setPalette(p)

        self._editor = QtWidgets.QLineEdit(self)
        self._editor.setWindowFlags(QtCore.Qt.Popup)
#         self._editor.setFocusProxy(self)
        self._editor.editingFinished.connect(self.handleEditingFinished)
        self._editor.installEventFilter(self)

    def eventFilter(self, widget, event):
        if ((event.type() == QtCore.QEvent.MouseButtonPress and
             not self._editor.geometry().contains(event.globalPos())) or
            (event.type() == QtCore.QEvent.KeyPress and
             event.key() == QtCore.Qt.Key_Escape)):
            self._editor.hide()
            return True
        return super().eventFilter(widget, event)

    def mouseDoubleClickEvent(self, _evt):
        self._editor.setText(self.text())
        self._editor.move(self.parent().mapToGlobal(self.pos()))
        self._editor.show()

    def handleEditingFinished(self):
        self._editor.hide()
        self.setText(self._editor.text())


class _LoadPreviewThread(QtCore.QThread):
    sigDone = QtCore.pyqtSignal(str, int, QtGui.QPixmap)  # , QtGui.QIcon)

    def __init__(self, path, row):
        QtCore.QThread.__init__(self)
        self.path = path
        self.row = row

    def run(self):
        pm = QtGui.QIcon(self.path).pixmap(100, 100)
        self.sigDone.emit(self.path, self.row, pm)


class _ProcessThread(QtCore.QThread):
    '''
    Thread to be used in tool.activate in order not to block
    the gui
    '''
    rowDone = QtCore.pyqtSignal(object, object, object)

    def __init__(self, rows, paths):  # , runfn, donefn=None):
        QtCore.QThread.__init__(self)
        self.rows = rows
        self.paths = paths
#         self.progressBar = tool.display.workspace.gui.progressBar
#         self.runfn = runfn
#         self._exc_info = None
#
#         self.sigDone.connect(self.done)
#         if donefn is not None:
#             self.sigDone.connect(donefn)
#

    def kill(self):
        self.terminate()

    def run(self):

        for i, (row, path) in enumerate(zip(self.rows, self.paths)):
            # try to read metadata:
            out = metaData(path)

            progress = (i + 1) / len(self.paths) * 100  # %
            self.rowDone.emit(progress, row, out  # , QtGui.QIcon(path)
                              )
#             self.rowDone.emit(progress, row, out)


#
#         self.progressBar.show()
#         self.progressBar.cancel.clicked.connect(self.kill)
#         self.progressBar.bar.setValue(50)
#         self.sigUpdate.connect(self.progressBar.bar.setValue)
#         self.progressBar.label.setText(
#             "Processing %s" %
#             self.tool.__class__.__name__)
#         QtCore.QThread.start(self)
#
#     def done(self):
#         self.progressBar.hide()
#         self.progressBar.cancel.clicked.disconnect(self.kill)
#
#     def run(self):
#         try:
#             out = self.runfn()
#         except (cv2.error, Exception, AssertionError) as e:
#             if type(e) is cv2.error:
#                 print(e)
#             self.progressBar.cancel.click()
#             self._exc_info = sys.exc_info()
#             return
#
#         self.sigDone.emit(out)
