import base64
from PyQt5 import QtWidgets, QtGui, QtCore
import json
from fancytools.os.PathStr import PathStr
# LOCAL
from client.widgets.ButtonGroupBox import ButtonGroupBox
from client.dialogs import FilenameInputDialog
from client.html import imageToHTML
from client.html import toHtml

IMG_HELP = PathStr(__file__).dirname().dirname().join('media', 'help')


class TabConfig(QtWidgets.QScrollArea):
    def __init__(self, gui):
        super(). __init__()
        self.gui = gui
        self.setWidgetResizable(True)

        self.inner = QtWidgets.QFrame(self)
        linner = QtWidgets.QHBoxLayout()
        self.inner.setLayout(linner)

        self.setWidget(self.inner)

        a = self.analysis = _Analysis(gui)
        self.location = _Location(self)
        self.modules = _ModTable(self, gui)

        self._addW(self.analysis, 'General', self.analysis)
        self._modulesGroup = self._addW(self.modules, 'Modules',
                                        horiz_stretch=True,
                                        vert_stretch=True)

        self._addW(self.location, 'Location', self.location)

        a.cbEnergyLoss.toggled.connect(self.cbEnergyLoss_clicked)
        a.cbEnergyLoss.toggled.connect(self._checkSetModulesTableEnabled)
        a.cbPerf.toggled.connect(self._checkSetModulesTableEnabled)
        a.cbQual.toggled.connect(self._checkSetModulesTableEnabled)

        a.cbQual.toggled.connect(lambda checked:
                                 self.modules.setColumnHidden(1, not checked))
        a.cbPerf.toggled.connect(lambda checked:
                                 self.modules.setColumnHidden(2, not checked))
        [self.modules.setColumnHidden(i, True) for i in range(1, 6)]

        self.cbEnergyLoss_clicked(a.cbEnergyLoss.isEnabled())
        self._checkSetModulesTableEnabled()

    def checkValid(self):
        '''returns whether configuration is complete
        '''
        return self.modules.checkValid()

    def _checkSetModulesTableEnabled(self):
        a = self.analysis
        v = (a.cbEnergyLoss.isChecked() or
             a.cbPerf.isChecked() or
             a.cbQual.isChecked())
        self._modulesGroup.setVisible(v)
        self.modules._isVisible = v

    def cbEnergyLoss_clicked(self, enabled):
        self.location.setVisible(enabled)
        t = self.modules
        [t.setColumnHidden(
            i, not enabled) for i in range(3, 6)]
#         t.resizeColumnsToContents()
        t.update()

    def _addW(self, w, name, g=None, horiz_stretch=False, vert_stretch=False):
        if g is None:
            g = QtWidgets.QGroupBox(name)
        ll = QtWidgets.QVBoxLayout()
        ll.setContentsMargins(1, 1, 1, 1)

        g.setLayout(ll)
        ll.addWidget(w)
        if not vert_stretch:
            ll.addStretch()
        self.inner.layout().addWidget(g, stretch=1 if horiz_stretch else 0)
        return g

    def toStr(self):
        config = {}
        config['modules'] = self.modules.config()
        config['analysis'] = self.analysis.config()
        config['location'] = self.location.config()
        return json.dumps(config, indent=4)

    # TODO: better names??
#     def saveToFile(self, path):
#         config = {}
#         # self.gui.camera.config()  # TODO: put in own tab
# #         config['camera'] = {'name': self.camOpts.currentText()}
#         config['modules'] = self.modules.config()
#         config['analysis'] = self.analysis.config()
#         config['location'] = self.location.config()
#
#         with open(path, 'w') as f:
#             f.write(json.dumps(config, indent=4))

    # TODO: better names??
    def restore(self, config):
        if len(config):
            #             self.gui.camera.restore(config['camera'])
            #             self.analysis.camOpts.addItem(config['camera']['name'])
            #             self.analysis.camOpts.setCurrentIndex(
            #                 self.analysis.camOpts.count() - 1)
            try:
                self.modules.restore(config['modules'])
                self.analysis.restore(config['analyze'])
                self.location.restore(config['location'])

            except KeyError:  # TODO: remove
                pass


class _StartThread(QtCore.QThread):

    def __init__(self):
        self.geolocator = None
        super().__init__()

    def run(self):
        # save startup time:
        from geopy.geocoders import Nominatim
        self.geolocator = Nominatim()


class _LocGroupBox(ButtonGroupBox):

    def __init__(self, name, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.parent = parent
        self.btn.clicked.connect(lambda: parent.closeGroup(self))

        # only allow removing current group if there is at least one
        # other module group still there:
        def fn():
            gr = parent.groups
            if gr:
                gr[0].btn.setEnabled(len(gr) > 1)
            else:
                self.btn.setEnabled(False)
        self.btn.clicked.connect(fn)
        fn()

        self.btn.setIcon(QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.SP_TitleBarCloseButton))

#         self.layout().addWidget(self.groupBox)
        ltop = QtWidgets.QVBoxLayout()
        self.setLayout(ltop)
#         ltop = self.layout()

#         ll = QtWidgets.QGridLayout()

        lll = QtWidgets.QGridLayout()

        ltop.addLayout(lll)
#         self.setLayout(lll)

        self.edName = QtWidgets.QLineEdit()
        self._oldLocName = name
        self.edName.setPlaceholderText(name)
        self.edName.textChanged.connect(self._edNameChanged)
        self._edAdress = QtWidgets.QLineEdit()
        self._edAdress.setPlaceholderText("7 Engineering Drive 1, Singapore")
        self._edAdress.returnPressed.connect(self._locationChanged)
        btn = QtWidgets.QPushButton("Lookup address")
        btn.clicked.connect(self._locationChanged)

        self._labFoundAddress = QtWidgets.QLabel()
#         self._labFoundAddress.setText("Found: ")

        lab1 = QtWidgets.QLabel("Latitude")
        lab2 = QtWidgets.QLabel("Longitude")

        self.edLong = QtWidgets.QLineEdit()
        self.edLong.setText('13.3765983')
        self.edLong.setValidator(QtGui.QDoubleValidator())

        self.edLat = QtWidgets.QLineEdit()
        self.edLat.setText('52.5094982')
        self.edLat.setValidator(QtGui.QDoubleValidator())

        lll.addWidget(self.edName, 0, 0)

        l2 = QtWidgets.QHBoxLayout()
        l2.addWidget(self._edAdress)
        l2.addWidget(btn)
        lll.addLayout(l2, 0, 1)

        lll.addWidget(self._labFoundAddress, 1, 0, 1, 3, QtCore.Qt.AlignRight)

        lll.addWidget(lab1, 2, 0)
        lll.addWidget(self.edLong, 2, 1)

        lll.addWidget(lab2, 3, 0)
        lll.addWidget(self.edLat, 3, 1)

        l6 = QtWidgets.QHBoxLayout()

        lll.addLayout(l6, 4, 1)

    def _edNameChanged(self, newname):
        self.parent.updateLocation(self._oldLocName, newname)
        self._oldLocName = newname

    def _locationChanged(self):
        loc = self._edAdress.text()
        if loc and self.parent._th.geolocator:
            location = self.parent._th.geolocator.geocode(loc)
            if location:
                self._labFoundAddress.setText(  # "Found: " +
                    location.address.replace(', ', '\n'))
                self.edLong.setText(str(location.longitude))
                self.edLat.setText(str(location.latitude))
            else:
                self._labFoundAddress.setText('')  # "Found: ")
                self.edLong.setText('nothing')
                self.edLat.setText('nothing')


class _Location(ButtonGroupBox):
    def __init__(self, tabconfig):
        super().__init__("  Location")
        self.tabconfig = tabconfig
        self._th = _StartThread()
        self._th.start()

        ltop = QtWidgets.QVBoxLayout()
        self.setLayout(ltop)
        self.btn.setText("+")
        self.btn.clicked.connect(self.add)

        self.groups = []
        self.add()
        ltop.addStretch()

    def updateLocation(self, old, new):
        T = self.tabconfig.modules
        for row in range(T.rowCount()):
            i = T.item(row, 5)
            if i is not None and i.text() == old:
                i.setText(new)

    def closeGroup(self, g):
        self.groups.remove(g)
        g.close()

    def add(self):
        lg = len(self.groups)
        name = 'Loc%i' % (lg + 1)
        g = _LocGroupBox(name, parent=self)
        self.groups.append(g)
        self.layout().insertWidget(lg, g)
        return name

    def config(self):
        return {}  # 'name': self.camOpts.currentText()}

    def restore(self, c):
        pass


class _Delegate_ID(QtWidgets.QItemDelegate):
    def __init__(self, table, gui, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gui = gui
        self.table = table

    def createEditor(self, parent, *_args, **_kwargs):
        comboType = QtWidgets.QComboBox(parent)
        mod = self.gui.modules()
        for row in range(self.table.rowCount()):
            i = self.table.item(row, 0)
            if i is not None:
                try:
                    mod.remove(i.text())
                except ValueError:
                    pass
        comboType.addItems(mod)
        return comboType


class _Delegate_typ(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        comboType = QtWidgets.QComboBox(parent)
        comboType.addItems(['mSi', 'pSi', 'aSi', 'CdTe'])
        return comboType


class _Delegate_width(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setRange(0.1, 3)
        return editor


class _Delegate_isc(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        editor = QtWidgets.QDoubleSpinBox(parent)

        editor.setRange(0.1, 12)
        return editor


class _Delegate_tcoeff(QtWidgets.QItemDelegate):

    def createEditor(self, parent, *_args, **_kwargs):
        spNOCT = QtWidgets.QDoubleSpinBox(parent)
        spNOCT.setRange(0, 100)
#         spNOCT.setValue(-1.5)
#         spNOCT.setSuffix(' %/°C')
        return spNOCT


class _Delegate_loc(QtWidgets.QItemDelegate):
    def __init__(self, config, *args, **kwargs):
        self.tabconfig = config
        super().__init__(*args, **kwargs)

    def _getLocations(self):
        ll = self.tabconfig.location.groups
        return [l.edName.text() if l.edName.text()
                else l.edName.placeholderText() for l in ll]

    def createEditor(self, parent, *_args, **_kwargs):
        comboType = QtWidgets.QComboBox(parent)
        loc = self._getLocations()
        comboType.addItems(loc)
        return comboType


class _ModTable(QtWidgets.QTableWidget):
    def __init__(self, config, gui):
        super().__init__(2, 6)
        self.tabconfig = config
        self.gui = gui

        [self.setColumnWidth(n, width)
         for n, width in enumerate([40, 50, 70, 70, 50])]

        LABELS = ['ID\n', 'Width*\n[m]', "I_sc\n[A]",
                  'Typ\n', 'T_coeff\n[-%/°C]', 'Location\n']
        self.setHorizontalHeaderLabels(LABELS)
#         item = QtWidgets.QTableWidgetItem()
#         item.setText("I<sub>mpp</sub>\n[A]")
#         self.setHorizontalHeaderItem(2, item)

        # draw top header frame :
        header = self.horizontalHeader()
        header.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        header.setLineWidth(1)
        self.setHorizontalHeader(header)
        # tooltips:
        headerItem = self.horizontalHeaderItem(1)
        headerItem.setToolTip(imageToHTML(
            IMG_HELP.join('hint_moduleSize.svg')))

        # save delegates, otherwise garbage collections causes crash
        # when multiple delegated are set via setItemDelegateForColumn
        self._delegates = (_Delegate_ID(self, self.gui), _Delegate_width(),
                           _Delegate_isc(), _Delegate_typ(),
                           _Delegate_tcoeff(), _Delegate_loc(self.tabconfig))
        [self.setItemDelegateForColumn(
            col, self._delegates[col]) for col in range(len(self._delegates))]

        self.verticalHeader().setVisible(False)
        h = self.horizontalHeader()
        h.setSectionResizeMode(h.Stretch)
#         h.setStretchLastSection(True)

        self.currentCellChanged.connect(self._addOrRemoveRows)

    def checkValid(self):
        # check whether mod table is visible ... which means it should be
        # filled:
        #         isvisible = False
        #         for c in range(self.columnCount()):
        #             print(c, self.isColumnHidden(c))
        #             if not self.isColumnHidden(c):
        #                 isvisible = True
        #                 break
        if not self._isVisible:
            return True
        # check whether all mod ids are entered:
        nid = 0
        orow, xrow = [], []  # filled and empty cells (ID)
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.text():
                nid += 1
                orow.append(row)
            else:
                xrow.append(row)
        if nid != len(self.gui.modules()):
            self.gui.tabs.setCurrentWidget(self.tabconfig)
            items = []
            for row in xrow:
                item = self.item2(row, 0)
                item.setBackground(QtGui.QBrush(QtCore.Qt.red))
                items.append(item)
            QtWidgets.QMessageBox.critical(self, "ID column incomplete",
                                           "Please fill in all module IDs")
            bg = QtWidgets.QTableWidgetItem().background()
            for item in items:
                item.setBackground(bg)

        # check whether all other visible cells where a module id is defined as
        # filled
        items = []
        for row in orow:
            for c in range(1, self.columnCount()):
                if not self.isColumnHidden(c):
                    item = self.item2(row, c)
                    if not item.text():
                        items.append(item)
                        item.setBackground(QtGui.QBrush(QtCore.Qt.red))
        if items:
            self.gui.tabs.setCurrentWidget(self.tabconfig)
            QtWidgets.QMessageBox.critical(self, "ID parameter incomplete",
                                           "Please fill in all parameters")
            bg = QtWidgets.QTableWidgetItem().background()
            for item in items:
                item.setBackground(bg)
            return False

        return True

    def item2(self, row, col):
        # TODO:move to baseclass
        item = self.item(row, col)
        if not item:
            item = QtWidgets.QTableWidgetItem()
            self.setItem(row, col, item)
        return item

    def keyPressEvent(self, evt):
        if evt.matches(QtGui.QKeySequence.Delete):
            for ran in self.selectedRanges():
                for row in range(ran.bottomRow(), ran.topRow() - 1, -1):
                    if row > 1:
                        self.removeRow(row)
        else:
            super().keyPressEvent(evt)

    def _addOrRemoveRows(self, row):
        if row == self.rowCount() - 1:
            self.setRowCount(row + 2)
        else:
            for r in range(self.rowCount() - 1, row + 1, -1):
                empty = True
                for col in range(self.columnCount()):
                    item = self.item(r, col)
                    if item is not None and item.text():
                        empty = False
                if empty:
                    self.setRowCount(r)

    def config(self):
        return {}  # 'name': self.camOpts.currentText()}

    def restore(self, c):
        pass


# class _Modules(QtWidgets.QWidget):
#     def __init__(self, config):
#         super().__init__()
#
# #         self.gui = gui
#
#         # update table, every time, when TabCheck has ned IDS
#         # and when images were imgported
#         # addnew devices to end
#
#         ll = QtWidgets.QVBoxLayout()
#         self.setLayout(ll)
#
# #         btn = QtWidgets.QPushButton('Update')
# #         ll.addWidget(btn, alignment=QtCore.Qt.AlignLeft)
#
#         self.table = _ModTable()
#         ll.addWidget(self.table)
#


class _Analysis(QtWidgets.QWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        ll = QtWidgets.QVBoxLayout()
        self.setLayout(ll)

        g0 = QtWidgets.QGroupBox('General options')
        g1 = QtWidgets.QGroupBox('Camera')
        g = QtWidgets.QGroupBox('Correct images (free)')
        self.btnPP = g2 = QtWidgets.QGroupBox(
            'Post processing (1S$ per measurement)')

        ll.addWidget(g0)
        ll.addWidget(g1)
        ll.addWidget(g)
        ll.addWidget(g2)
        ll.addStretch()

        #<<<<GENERAL SECTION
        lab = QtWidgets.QLabel(" image viewer")
        self.cbViewer = cb = QtWidgets.QComboBox()
        cb.addItems(("OS default", "Inline", 'dataArtist'))
        l0 = QtWidgets.QVBoxLayout()
        l01 = QtWidgets.QHBoxLayout()
        l01.addWidget(cb)
        l01.addWidget(lab)
        l01.addStretch()

        self._cb2fa = QtWidgets.QCheckBox('2 factor authorization')
        self._cb2fa.setToolTip("""Keep checked to receive an authorization code every time you login,
Be aware that although switching option off will save you time, your account can be easily 
taken over by everyone who has your password.""")
        if gui:
            self._cb2fa.setChecked(gui.server.requires2FA())
            self._cb2fa.clicked.connect(gui.server.setRequires2FA)

        autologin = QtWidgets.QCheckBox('Auto-login last user')
        if gui:
            self._filePwd = gui.PATH_USER.join('pwd')
            self._cb2fa.setToolTip("""If checked, user password will saved in %s. 
The last user will automatically logged in at every new start, 
until this option is switched off.""" % self._filePwd)
            autologin.setChecked(self._filePwd.exists())
            if autologin.isChecked():
                self._cb2fa.setEnabled(False)
        autologin.clicked.connect(self._changeAutologin)

        g0.setLayout(l0)
        l0.addLayout(l01)
        l0.addWidget(self._cb2fa)
        l0.addWidget(autologin)

        #<<<CAMERA SECTION:
        l1 = QtWidgets.QVBoxLayout()
        l11 = QtWidgets.QHBoxLayout()
        l1.addLayout(l11)

        g1.setLayout(l1)

        self.camOpts = QtWidgets.QComboBox()
        if gui:
            self.camOpts.addItems(gui.server.availCameras())

        btnAdd = QtWidgets.QToolButton()
        btnAdd.setText('+')
        btnAdd.setAutoRaise(True)

        ckCal = QtWidgets.QCheckBox('Use own camera calibration')
        ckCal.setToolTip(''''By default a camera calibration is generated by the images 
provided and no camera calibration is needed. However, the quality of camera correction can possibly be increased 
if an camera calibration is conducted. Check this box to use your own calibration as obtained with dataArtist''')
        # FIXME: make upload of own calibrations possible
        ckCal.clicked.connect(lambda _: [QtWidgets.QMessageBox.warning(
            self, 'Not implemented', 'At the moment it is not possible to use an own camera calibration. Sorry.'
        ), ckCal.setChecked(False), ckCal.setEnabled(False)])
        btnAdd.clicked.connect(self._newCamera)

        self.ckLight = QtWidgets.QCheckBox("Variable light conditions")
        txt = """Check this box, if measurements are NOT done in a light-tight chamber
or the environmental light conditions change in every measurement 
(e.g. outdoor measurements).
If your background images look like this ...%s 
You can uncheck this box.
If however you background images look like this... %s 
You should ensure, that light does not change
during measurements.

If this option is checked, no background calibration will be generated.
Therefore for background correction at least one background 
image for every measurement is essential.""" % (
              imageToHTML(IMG_HELP.join('bg_noStraylight.jpg')),
              imageToHTML(IMG_HELP.join('bg_straylight.jpg')))
        self.ckLight.setToolTip(toHtml(txt))

        l11.addWidget(self.camOpts)
        l11.addWidget(btnAdd)
        l11.addStretch()
        l1.addWidget(ckCal)
        l1.addWidget(self.ckLight)

        #<<<<CORRECT IMAGES SECTION
        lll = QtWidgets.QVBoxLayout()
        g.setLayout(lll)

        g2.setCheckable(True)
        g2.setChecked(False)
        g2.toggled.connect(self._postProcessingToggled)

        lll2 = QtWidgets.QVBoxLayout()
        g2.setLayout(lll2)

        self.cbSize = QtWidgets.QCheckBox("Fixed output size")
        self.cbSize.setToolTip(
            '''If this parameter is not checked, 
image size of the corrected image will be determined according to input image''')
        self.sizeX = QtWidgets.QSpinBox()
        self.sizeX.setPrefix('x ')
        self.sizeX.setRange(0, 20000)
        self.sizeX.setValue(4000)

        self.sizeX.setEnabled(False)

        self.sizeY = QtWidgets.QSpinBox()
        self.sizeY.setPrefix('y ')
        self.sizeY.setRange(0, 20000)
        self.sizeY.setValue(2400)
        self.sizeY.setEnabled(False)

        self.cbSize.clicked.connect(self.sizeX.setEnabled)
        self.cbSize.clicked.connect(self.sizeY.setEnabled)

        lSize = QtWidgets.QHBoxLayout()
        lSize.addWidget(self.cbSize)
        lSize.addWidget(self.sizeX)
        lSize.addWidget(self.sizeY)
        lSize.addStretch(1)

        self.cbDeformed = QtWidgets.QCheckBox("Devices might be deformed")
        self.cbDeformed.setToolTip('''Check this parameter, 
if mechanical deformation of the imaged device cannot be ruled out.''')

        self.cbPos = QtWidgets.QCheckBox(
            "Device position changes during measurement")
        self.cbPos.setToolTip(
            '''Check this parameter, 
if the device position differs for different currents in one measurement.''')

        # TODO: should be always done, or?
        self.cbPrecise = QtWidgets.QCheckBox("Precise alignment")
        self.cbPrecise.setToolTip('This option increases calculation time')
        self.cbPrecise.setChecked(True)

        self.cbArtifacts = QtWidgets.QCheckBox("Remove artifacts")
        self.cbArtifacts.setToolTip('Filter erroneous pixels')
        self.cbArtifacts.setChecked(True)

        lcorr = QtWidgets.QHBoxLayout()
        lcorrW = QtWidgets.QVBoxLayout()
        lcorr.addLayout(lcorrW)
        lcorrW.addLayout(lSize)

        lcorrW.addWidget(self.cbDeformed)
        lcorrW.addWidget(self.cbPos)
        lcorrW.addWidget(self.cbPrecise)
        lcorrW.addWidget(self.cbArtifacts)

        #<<<<POSTPROCESSING SECTION
        self.cbQual = cb0 = QtWidgets.QCheckBox(
            "Calculate image quality")
        cb0.setChecked(False)

        self.cbUncert = cb01 = QtWidgets.QCheckBox("Map uncertainty")

        self.cbEnhance = QtWidgets.QCheckBox(
            "Enhance image (sharpen, denoise)")
        self.cbEnhance.setToolTip(
            'Create an additional sharpened and denoised image')

        self.cbPerf = cb1 = QtWidgets.QCheckBox("Estimate Power loss")
        cb1.setToolTip(
            'Calculate the power loss relative to initial measurement')

        self.cbEnergyLoss = cb11 = QtWidgets.QCheckBox("+ Energy loss")
        self._makeCBdependant(cb11, cb1)

        cb12 = QtWidgets.QCheckBox("Detect features")
        cb12.setToolTip(
            'Detect and measure cracks and inactive areas')

        self.cbReport = QtWidgets.QCheckBox(
            "Write report")

        self.cbMail = QtWidgets.QCheckBox("Send report via mail")

        self._makeCBdependant(cb01, cb0)
        self._makeCBdependant(self.cbEnhance, cb0)

        lll.addLayout(lcorr)
        lll2.addWidget(cb0)

        self._addIndented(cb01, lll2)
        self._addIndented(self.cbEnhance, lll2)

        lll2.addWidget(cb1)
        self._addIndented(cb11, lll2)
        lll2.addWidget(cb12)

        self.cbManual = cb2 = QtWidgets.QCheckBox(
            "Ask an engineer to evaluate the results")

        self.manualEditor = editor = QtWidgets.QTextEdit()
        editor.setPlaceholderText(
            "Problem description\nFurther instructions\netc.")
        editor.hide()  # setEnabled(False)
        cb2.clicked.connect(editor.setVisible)

        lll2.addWidget(self.cbReport)
        self._addIndented(self.cbMail, lll2)
        self._addIndented(cb2, lll2)
        self._addIndented(editor, lll2)

        self._makeCBdependant(self.cbMail, self.cbReport)
        self._makeCBdependant(self.cbManual, self.cbReport)

    def _changeAutologin(self, enable):
        if not enable:
            if self._filePwd.exists():
                self._filePwd.remove()
        else:
            self._cb2fa.setChecked(False)
            self._cb2fa.setEnabled(False)

            if self.gui.pwd is None:
                self.gui.pwd = QtWidgets.QInputDialog.getText(self, 'Re-enter password',
                                                              'Please enter you password again')

            with open(self._filePwd, 'wb') as f:
                # this is obviously not a save way to store a password,
                # but for decrypting, the villain has to know some python
                # and has to find this code
                encrypted = base64.b64encode(self.gui.pwd.encode())
                f.write(encrypted)

    def _newCamera(self):
        f = FilenameInputDialog('New camera', 'Name:')
        f.exec_()
        if f.result() == f.Accepted:
            self.camOpts.addItem(f.text())
            self.camOpts.setCurrentIndex(self.camOpts.count() - 1)

    def _postProcessingToggled(self, checked):
        if not checked:
            if self.cbPerf.isChecked():
                self.cbPerf.toggle()
            if self.cbQual.isChecked():
                self.cbQual.toggle()

    @staticmethod
    def _makeCBdependant(cb, cbparent):
        '''
        disable/uncheck <cb> is <parentcb> is unchecked
        '''
        cb.setEnabled(cbparent.isChecked())

        def fn(checked):
            if not checked:
                cb.setChecked(False)
            cb.setEnabled(checked)
        cbparent.toggled.connect(lambda checked: fn(checked))

    def _addIndented(self, widget, layout):
        ll = QtWidgets.QHBoxLayout()
        ll.addSpacing(20)
        ll.addWidget(widget)
        layout.addLayout(ll)

    def config(self):
        sf = self.cbSize.isChecked()
        if sf:
            s = self.sizeY.value(), self.sizeX.value()
        else:
            s = None
        return {'calc_quality': self.cbQual.isChecked(),
                'calc_uncertainty': self.cbUncert.isChecked(),
                'post_processing': self.btnPP.isChecked(),
                'performance': self.cbPerf.isChecked(),
                'report_via_mail': self.cbMail.isChecked(),
                'manual': self.cbManual.isChecked(),
                'comments': self.manualEditor.toPlainText(),
                'fixed_output_size': sf,
                'output_image_size': s,
                'module_is_deformed': self.cbDeformed.isChecked(),
                'device_at_same_pos_for_diff_currents': self.cbPos.isChecked(),
                'sub_px_alignment': self.cbPrecise.isChecked(),
                'removeArtefacts': self.cbArtifacts.isChecked(),
                'enhance_image': self.cbEnhance.isChecked(),
                'variable_light_conditions': self.ckLight.isChecked()
                }

    def restore(self, c):
        self.cbQual.setChecked(c['calc_quality'])
        self.cbUncert.setChecked(c['calc_uncertainty'])
        self.btnPP.setChecked(c['post_processing'])
        self.cbPerf.setChecked(c['performance'])
        self.cbMail.setChecked(c['report_via_mail'])
        self.cbManual.setChecked(c['manual'])
        self.manualEditor.setPlainText(c['comments'])
        self.cbSize.setChecked(c['fixed_output_size'])
        self.sizeX.setValue(c['output_image_size'][1])
        self.sizeY.setValue(c['output_image_size'][0])
        self.cbDeformed.setChecked(c['module_is_deformed'])
        self.cbPos.setChecked(c['device_at_same_pos_for_diff_currents'])
        self.cbPrecise.setChecked(c['sub_px_alignment'])
        self.cbArtifacts.setChecked(c['removeArtefacts'])
        self.cbEnhance.setChecked(c['enhance_image'])
        self.ckLight.setChecked(c['variable_light_conditions'])


if __name__ == '__main__':
    import sys
    #######################
    # temporary fix: app crack doesnt through exception
    # https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
    sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
    #######################
    app = QtWidgets.QApplication([])
    w = TabConfig(None)
    w.resize(1100, 600)

#     w.restore(w.config())

    w.show()
    app.exec_()
