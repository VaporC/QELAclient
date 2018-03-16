# -*- coding: utf-8 -*-
import numpy as np

from PyQt5 import QtWidgets, QtCore

from fancytools.utils import json2 as json
from imgProcessor.imgIO import imread

# local
from client.communication.utils import agendaFromChanged
from client.widgets.Contact import Contact
from client.widgets.GridEditor import CompareGridEditor


class QTreeWidget(QtWidgets.QTreeWidget):

    def getAffectedItems(self):
        '''return list of all items in currently selected tree
        e.g.:
        Ia
            IIa <-- selected
                IIIa
        Ib
            IIb
                IIIb

        returns [Ia,IIa,IIIa]
        '''
        out = []

        def _fn(item):
            ii = item.childCount()
            if ii:
                # go down to last child
                for i in range(ii):
                    ch = item.child(i)
                    _fn(ch)
            else:
                # build list [topitem, child, childchild...]
                out.append(item)
        _fn(self.currentItem())
        return out

    def recursiveItemsText(self, item=None, col=0):
        # TODO: if practically recursiveItems but with text instead of
        # items ... shorten
        if item is None:
            item = self.invisibleRootItem()
        for i in range(item.childCount()):
            ch = item.child(i)
            yield from self.recursiveItemsText(ch, col)
        if item != self.invisibleRootItem():
            out = self.itemInheranceText(item)
            yield (item, out)

    @staticmethod
    def itemInherence(item):
        out = [item]
        while True:
            p = item.parent()
            if not p:
                break
            out.insert(0, p)
            item = p
        return out

    @classmethod
    def itemInheranceText(cls, item, col=0):
        return [i.text(col) for i in cls.itemInherence(item)]

    @staticmethod
    def findChildItem(parent, name, col=0):
        for i in range(parent.childCount()):
            if parent.child(i).text(col) == name:
                return parent.child(i)

    def buildCheckTree(self, item=None, nintent=0):
        """
        output:
            [(ID0,0,{...}),(meas0,1),(cur0,2,{...}),(cur1,2,{...}),...]
        """
        if item is None:
            item = self.invisibleRootItem()
        for i in range(item.childCount()):
            ch = item.child(i)
            yield from self.buildCheckTree(ch, nintent + 1)
        if item != self.invisibleRootItem():
            yield (item, nintent - 1)


class TabCheck(QtWidgets.QSplitter):
    help = '''Although applied image processing routines automatically detect
PV modules and cells, manual verification / modification can be needed
in case device corners and grid parameters were detected wrongly or the camera correction
causes erroneous results.
XXXXXXXXXXXXXXX
    '''

    def __init__(self, gui=None):
        super().__init__()

        self.gui = gui
        self.vertices_list = []
        self._lastP = None

        self._grid = CompareGridEditor()
        self._grid.gridChanged.connect(self._updateGrid)
#         self._grid.cornerChanged.connect(self._updateCorner)
        self._grid.verticesChanged.connect(self._updateVertices)

        self.btn_markCurrentDone = QtWidgets.QPushButton("Mark verified")
        self.btn_markCurrentDone.clicked.connect(self._toggleVerified)

        self._grid.bottomLayout.addWidget(self.btn_markCurrentDone, 0, 0)

        self.list = QTreeWidget()
        self.list.setHeaderHidden(True)

        btnReset = QtWidgets.QPushButton('Reset')
        btnReset.clicked.connect(self._resetAll)

        btnSubmit = QtWidgets.QPushButton('Submit')
        btnSubmit.clicked.connect(self._acceptAll)

        llist = QtWidgets.QHBoxLayout()
        llist.addWidget(QtWidgets.QLabel("All:"))
        llist.addWidget(btnReset)
        llist.addWidget(btnSubmit)
        llist.addStretch()

        l3 = QtWidgets.QVBoxLayout()
        l3.addLayout(llist)
        l3.addWidget(self.list)

        btn_actions = QtWidgets.QPushButton("Actions")
        menu = QtWidgets.QMenu()

        menu.addAction("Reset changes").triggered.connect(self._resetChanges)
        a = menu.addAction("Recalculate all measurements")
        a.setToolTip('''Choose this option to run image processing on all submitted images
of the selected module again. This is useful, since QELA image processing routines are continuously developed
and higher quality results can be available. Additionally, this option will define a new 
template image (the image other images are perspectively aligned to) depending on the highest resolution/quality  
image within the image set.''')
        a.triggered.connect(self._processAllAgain)

        menu.addAction("Report a problem"
                       ).triggered.connect(self._reportProblem)
        menu.addAction("Upload images again").triggered.connect(
            self._uploadAgain)
        menu.addAction("Remove measurement").triggered.connect(
            self._removeMeasurement)

        btn_actions.setMenu(menu)
        l3.addWidget(btn_actions)

        wleft = QtWidgets.QWidget()
        wleft.setLayout(l3)
        self.addWidget(wleft)
        self.addWidget(self._grid)

        self.list.currentItemChanged.connect(self._loadImg)

        if self.gui is not None:
            self._timer = QtCore.QTimer()
            self._timer.setInterval(3000)
            self._timer.timeout.connect(self.checkUpdates)
            self._timer.start()

    def _processAllAgain(self):
        # TODO
        reply = QtWidgets.QMessageBox.question(
            self, 'TOD:', "This option is not available at the moment, SORRY",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

    def _uploadAgain(self):
        items = self.list.getAffectedItems()
        lines = []
        for item in items:
            data = item.data(1,  QtCore.Qt.UserRole)

            agenda = self.gui.PATH_USER.join(
                'upload', data['timestamp'] + '.csv')
            lines.extend(agendaFromChanged(agenda, data))

        self.gui.tabUpload.dropLines(lines)

    def _getAffectedPaths(self):
        items = self.list.getAffectedItems()
        out = []
        for item in items:
            p = item.parent()
            pp = p.parent()
            out.append("%s\\%s\\%s" % (
                pp.text(0), p.text(0), item.text(0)))
        return out

    def _removeMeasurement(self):
        affected = self._getAffectedPaths()
        if affected:
            box = QtWidgets.QMessageBox()
            box.setStandardButtons(box.Ok | box.Cancel)
            box.setWindowTitle('Remove measurement')
            box.setText("Do you want to remove ...\n%s" % "\n".join(affected))
            box.exec_()

            if box.result() == box.Ok:
                self.gui.server.removeMeasurements(*affected)
                self.checkUpdates()

    def _reportProblem(self):
        ID, meas, cur = self._getIDmeasCur()
        self._contact = Contact(self.gui)
        self._contact.subject.setText('%s\\%s\\%s' % (
            ID.text(0), meas.text(0), cur.text(0)))
        self._contact.editor.text.setText(
            'E.g. bad image correction, \n   remaining vignetting, \n   image looks distorted')
        self._contact.show()

    def _resetAll(self):
        reply = QtWidgets.QMessageBox.question(
            self, 'Resetting all changes', "Are you sure?",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self._resetChanges(self.list.invisibleRootItem())

    def _resetChangesCurrentItem(self):
        item = self.list.currentItem()
        return self._resetChanges(item)

    def _excludeUnchangableKeys(self, data):
        if 'vertices' in data:
            return {k: data[k] for k in ['verified', 'vertices']}
        return data

    def _resetChanges(self, item):
        def _reset(item):
            data = item.data(1,  QtCore.Qt.UserRole)
            if data is not None:
                item.setData(0, QtCore.Qt.UserRole,
                             self._excludeUnchangableKeys(data))

            f = item.font(0)
            f.setBold(False)
            item.setFont(0, f)

            for i in range(item.childCount()):
                _reset(item.child(i))

        _reset(item)

        cur = self._getIDmeasCur()[2]
        data = cur.data(0,  QtCore.Qt.UserRole)
        self._grid.grid.setVertices(data['vertices'])

        self._changeVerifiedColor(item)

    def _isIDmodified(self, ID):
        data0 = ID.data(0, QtCore.Qt.UserRole)
        data1 = ID.data(1, QtCore.Qt.UserRole)
        return (data0['nsublines'] != data1['nsublines']
                or data0['grid'] != data1['grid'])

    def _updateVertices(self, vertices):
        cur = self._getIDmeasCur()[2]

        data = cur.data(1,  QtCore.Qt.UserRole)
        originalvertices = data['vertices']
        data['vertices'] = vertices
        cur.setData(0, QtCore.Qt.UserRole, data)

        changed = not np.allclose(
            vertices, np.array(originalvertices), rtol=0.01)

        f = cur.font(0)
        f.setBold(changed)
        cur.setFont(0, f)

    def _updateGrid(self, key, val):
        ID = self._getIDmeasCur()[0]
        data = ID.data(0, QtCore.Qt.UserRole)
        data[key] = val
        ID.setData(0, QtCore.Qt.UserRole, data)
        f = ID.font(0)
        changed = self._isIDmodified(ID)
        f.setBold(changed)
        ID.setFont(0, f)

    def _getIDmeasCur(self):
        '''
        returns current items for ID, measurement and current
        '''
        item = self.list.currentItem()
        p = item.parent()
        if p is not None:
            pp = p.parent()
            if pp is not None:
                ID, meas, cur = pp, p, item
            else:
                ID, meas, cur = p, item, item.child(0)
        else:
            ID, meas, cur = (item, item.child(0),
                             item.child(0).child(0))
        return ID, meas, cur

    def _loadImg(self):
        try:
            ID, meas, cur = self._getIDmeasCur()
            txt = ID.text(0), meas.text(0), cur.text(0)
            root = self.gui.projectFolder()
            p = root.join(*txt)
            if p == self._lastP:
                return
            self._lastP = p

            p0 = p.join("prev_A.jpg")
            p1 = p.join("prev_B.jpg")
            ll = len(root) + 1
            if not p0.exists():
                self.gui.server.download(p0[ll:], root)
            if not p1.exists():
                self.gui.server.download(p1[ll:], root)

            img = imread(p0)
            self._grid.imageview.setImage(img, autoRange=False)

            img = imread(p1)
            self._grid.imageview2.setImage(img, autoRange=False)

            # load/change grid
            cells = ID.data(0,  QtCore.Qt.UserRole)['grid']
            nsublines = ID.data(0,  QtCore.Qt.UserRole)['nsublines']

            cdata = cur.data(0,  QtCore.Qt.UserRole)
#             print(1111123, self._grid.grid.vertices())
#             print(cdata['vertices'])
            vertices = cdata['vertices']

            # TODO: remove different conventions
#             cells = cells[::-1]
#             nsublines = nsublines[::-1]

            vertices = np.array(vertices)[np.array([0, 3, 2, 1])]
#             print(vertices, 9898)

            self._grid.grid.setNCells(cells)
            self._grid.grid.setVertices(vertices)
#             print(self._grid.grid.vertices(), 888888888888888888)

            self._grid.edX.setValue(cells[0])
            self._grid.edY.setValue(cells[1])
            self._grid.edBBX.setValue(nsublines[0])
            self._grid.edBBY.setValue(nsublines[1])
            self._updateBtnVerified(cdata['verified'])
        except AttributeError as e:
            print(e)

    def toggleShowTab(self, show):
        t = self.gui.tabs
        t.setTabEnabled(t.indexOf(self), show)

    def buildTree(self, tree):
        show = bool(tree)
        self.toggleShowTab(show)
        if show:
            root = self.list.invisibleRootItem()
            last = [root, None, None]

            def _addParam(name, params, nindents):
                if nindents:
                    parent = last[nindents - 1]
                else:
                    parent = root
                item = self.list.findChildItem(parent, name)
#                 if params:
#                     params = json.loads(params)
                if item is None:
                    item = QtWidgets.QTreeWidgetItem(parent, [name])
                    if params:
                        if nindents == 2:
                            # modifiable:
                            item.setData(0, QtCore.Qt.UserRole,
                                         self._excludeUnchangableKeys(params))
                        else:
                            # nindents==1 -> grid
                            item.setData(0, QtCore.Qt.UserRole, params)
                        self._changeVerifiedColor(item)
                last[nindents] = item
                if params:
                    params = params
                    # original:
                    item.setData(1, QtCore.Qt.UserRole, params)

            # add new items / update existing:
            treenames = []
            for ID, param, meas in tree:
                _addParam(ID, param, 0)
                treenames.append([ID])
                for m, currents in meas:
                    _addParam(m, None, 1)
                    treenames.append([ID, m])
                    for c, param in currents:
                        _addParam(c, param, 2)
                        treenames.append([ID, m, c])
            # remove items that are in client but not in server tree:
            for item, texts in self.list.recursiveItemsText():
                if texts not in treenames:
                    p = item.parent()
                    if not p:
                        p = root
                    p.takeChild(p.indexOfChild(item))
            root.sortChildren(0, QtCore.Qt.AscendingOrder)

            self.list.resizeColumnToContents(0)
            self.list.setCurrentItem(self.list.itemAt(0, 0))

    def modules(self):
        '''
        return generator for all module names in .list
        '''
        item = self.list.invisibleRootItem()
        for i in range(item.childCount()):
            yield item.child(i).text(0)

    def checkUpdates(self):
        if self.gui.server.isReady() and self.gui.server.hasNewCheckTree():
            self.buildTree(self.gui.server.checkTree())

    def _toggleVerified(self):
        item = self._getIDmeasCur()[2]
        data = item.data(0,  QtCore.Qt.UserRole)
        v = data['verified'] = not data['verified']
        item.setData(0, QtCore.Qt.UserRole, data)

        self._updateBtnVerified(v)
        self._changeVerifiedColor(item)

    def _updateBtnVerified(self, verified):
        if verified:
            self.btn_markCurrentDone.setText('Mark unverified')
        else:
            self.btn_markCurrentDone.setText('Mark verified    ')

    def _changeVerifiedColor(self, item):
        data = item.data(0,  QtCore.Qt.UserRole)
        if data is None or 'verified' not in data:
            return
        if data['verified']:
            color = QtCore.Qt.darkGreen
        else:
            color = QtCore.Qt.black
        item.setForeground(0, color)

        # apply upwards, if there is only one item in list
        while True:
            parent = item.parent()
            if not parent:
                break
            if parent.childCount() == 1:
                item = parent
                item.setForeground(0, color)

    def _acceptAll(self):
        reply = QtWidgets.QMessageBox.question(
            self, 'Submitting changes', "Are you sure?",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self._doSubmitAllChanges()

    def _doSubmitAllChanges(self):
        out = {'grid': {}, 'unchanged': {}, 'changed': {}}
        for item, nindent in self.list.buildCheckTree():
            data = item.data(0, QtCore.Qt.UserRole)
            if nindent == 1:
                # only grid and curr interesting
                continue
            path = '\\'.join(self.list.itemInheranceText(item))
            changed = item.font(0).bold()
            print(path, data, nindent)
            if nindent == 2:
                if changed:  # item is modified
                    out['changed'][path] = data
                else:
                    out['unchanged'][path] = data['verified']
            elif changed:
                out['grid'][path] = data  # ['verified']
        self.gui.server.submitChanges(json.dumps(out) + '<EOF>')

    def config(self):
        return {}  # 'name': self.camOpts.currentText()}

    def restore(self, c):
        pass
#         self.camOpts.addItem(c['name'])
#         self.camOpts.setCurrentIndex(self.camOpts.count() - 1)


if __name__ == '__main__':
    import sys
    from fancytools.os.PathStr import PathStr

    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])
    w = TabCheck()

    imgs = PathStr(
        r'D:\Measurements\TrinaPID_EL\EL\source\02ND ROUND\8A').files()
#     w.addImgs(imgs)

#     w.buildTree('''ID1 {"grid":[6,10], "sublines":[[],[]]}
#     meas1 {"vertices":[[[0, 0], [2, 0], [1, 1], [0, 1]]], "validated":0}
#         cur1
#         cur2
#     mea2 {"vertices":[[[0, 0], [2, 0], [1, 1], [0, 1]]], "validated":0}
#         cur1
#         cur2
# ID2
# ID3
# ''')


#     childItem = QtWidgets.QTreeWidgetItem(w.list.item(0))
#     w.list.item(0).insertChild(0, 'ss')

    w.show()
    app.exec_()
