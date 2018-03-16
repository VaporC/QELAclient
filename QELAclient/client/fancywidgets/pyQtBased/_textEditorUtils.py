# coding=utf-8
"""
text editor utils used by
* FwMinimalTextEditor
* FwTextEditor
"""

# foreign
import time
# , QtSvg # QtSvg has to be imported under windows to show svg icons
from PyQt5 import QtGui, QtPrintSupport, QtWidgets, QtCore
from PyQt5.QtCore import Qt
# own
from fancytools.os.PathStr import PathStr


from fancywidgets.pyQtBased.Dialogs import Dialogs
from fancywidgets.pyQtBased.SnippingTool import SnippingArea
from fancywidgets import media

var = 0
f = ""
choiceStr = ""
cs = False
wwo = False

tt = True
tf = True
ts = True

iconfolder = PathStr(
    media.__file__).dirname().join(
        "icons",
    "foundation-icon-fonts-3")
dialogs = Dialogs()


class MainWindow(QtWidgets.QMainWindow):  # rename

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowFlags(Qt.Widget)  # allow to use mainwindow as widget

        self.text = _TextEdit(self)
        self.text.setTabStopWidth(12)
        self.setCentralWidget(self.text)

    def showToolbar(self, show):
        self.text.showToolbarChecked = show
        for t in self.findChildren(QtWidgets.QToolBar):
            # for t in self.toolbars:
            if show:
                t.show()
            else:
                t.hide()

    def toHtml(self):
        '''
        TODO
        '''
        html0 = self.text.toHtml()
        html = html0
        doc = self.text.document()

        fimgs = {}  # fornam name: image format
        # go through tdocument to find all image formats:
        cursor = self.text.textCursor()
        success = cursor.movePosition(cursor.Start)
        while success:
            cf = cursor.charFormat()
            if cf.isImageFormat():
                f = cf.toImageFormat()
                fimgs[f.name()] = f
            success = cursor.movePosition(cursor.Right)
        # embedd images into html:
        html3 = ''
        end = None
        while True:
            try:
                i = html.index('src="mydata:') + 5
            except ValueError:
                break
            html2 = html[i:]
            end = html2.index('"')
            path = html2[:end]

            image = doc.resource(doc.ImageResource, QtCore.QUrl(path))

            f = fimgs[path]
            # rescale images acording to visible size:
            image = image.scaled(int(f.width()), int(f.height()))

            ba = QtCore.QByteArray()
            buf = QtCore.QBuffer(ba)
            buf.open(QtCore.QIODevice.WriteOnly)
            image.save(buf, 'PNG')
            encoded = ba.toBase64().data()
            html3 += html[:i] + "data:image/png;base64,%s" % encoded
            html = html2
        if end is not None:
            html3 += html[end:]
        return html3


class _TextEdit(QtWidgets.QTextEdit):
    """
    allow to show/hide the toolbar through context menu
    """

    def __init__(self, editor):
        self.editor = editor
        QtWidgets.QTextEdit.__init__(self, editor)
        self.showToolbarChecked = True
        self._imageSlider = None
        self._sliderModed = False
        self.cursorPositionChanged.connect(self._checkImageToRescale)

    def _resizeCurrentImage(self, val):
        f, img = self._currentImage

        val = val / 100
        f.setWidth(img.width() * val)
        f.setHeight(img.height() * val)

        pos = self._imageSlider.pos()  # to keep position

        cur = self.textCursor()
        cur.deletePreviousChar()
        cur.insertImage(f)

        self._imageSlider.move(pos)

    def _checkImageToRescale(self):
        if self._sliderModed:
            return
        cursor = self.textCursor()
        doc = self.document()

        cf = cursor.charFormat()
        if cf.isImageFormat():
            # ensure, that cursor is behind image:
            cursor.setPosition(cursor.position() + 1)
            if not cursor.charFormat().isImageFormat():
                cursor.setPosition(cursor.position() - 1)
            self.setTextCursor(cursor)

            f = cf.toImageFormat()
            path = f.name()
            img = doc.resource(doc.ImageResource, QtCore.QUrl(path))

            self._currentImage = f, img
            if self._imageSlider is not None:
                self._imageSlider.close()
            sl = self._imageSlider = QtWidgets.QSlider(self)
            sl.setWindowFlags(Qt.FramelessWindowHint)
            sl.setMinimum(1)
            sl.sliderPressed.connect(
                lambda: setattr(self, '_sliderModed', True))
            sl.sliderReleased.connect(
                lambda: setattr(self, '_sliderModed', False))
            sl.setValue(100 * f.width() / img.width())
            p = self.cursorRect().topRight()
            sl.move(p)

            sl.setAttribute(Qt.WA_TranslucentBackground)
            sl.show()
            sl.valueChanged.connect(self._resizeCurrentImage)

        elif self._imageSlider is not None:
            self._imageSlider.close()
            self._imageSlider = None

    def contextMenuEvent(self, event):
        menu = QtWidgets.QTextEdit.createStandardContextMenu(self)
        menu.addSeparator()

        a = QtWidgets.QAction('Show Toolbar', menu)
        a.triggered.connect(self.editor.showToolbar)
        a.triggered.connect(self._storeActionValueToolbarChecked)
        a.setCheckable(True)
        a.setChecked(self.showToolbarChecked)
        menu.addAction(a)

        menu.exec_(event.globalPos())

    def _storeActionValueToolbarChecked(self, checked):
        self.showToolbarChecked = checked


class Find(QtWidgets.QDialog):

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.initUI()

    def initUI(self):

        self.lb1 = QtWidgets.QLabel("Search for: ", self)
        self.lb1.setStyleSheet("font-size: 15px; ")
        self.lb1.move(10, 10)

        self.te = QtWidgets.QTextEdit(self)
        self.te.move(10, 40)
        self.te.resize(250, 25)

        self.src = QtWidgets.QPushButton("Find", self)
        self.src.move(270, 40)

        self.lb2 = QtWidgets.QLabel("Replace all by: ", self)
        self.lb2.setStyleSheet("font-size: 15px; ")
        self.lb2.move(10, 80)

        self.rp = QtWidgets.QTextEdit(self)
        self.rp.move(10, 110)
        self.rp.resize(250, 25)

        self.rpb = QtWidgets.QPushButton("Replace", self)
        self.rpb.move(270, 110)

        self.opt1 = QtWidgets.QCheckBox("Case sensitive", self)
        self.opt1.move(10, 160)
        self.opt1.stateChanged.connect(self.CS)

        self.opt2 = QtWidgets.QCheckBox("Whole words only", self)
        self.opt2.move(10, 190)
        self.opt2.stateChanged.connect(self.WWO)

        self.close = QtWidgets.QPushButton("Close", self)
        self.close.move(270, 220)
        self.close.clicked.connect(self.Close)

        self.setGeometry(300, 300, 360, 250)

    def CS(self, state):
        global cs

        if state == QtCore.Qt.Checked:
            cs = True
        else:
            cs = False

    def WWO(self, state):
        global wwo
    #    print(wwo)

        if state == QtCore.Qt.Checked:
            wwo = True
        else:
            wwo = False

    def Close(self):
        self.hide()


class Date(QtWidgets.QDialog):

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.initUI()

    def initUI(self):

        self.form = QtWidgets.QComboBox(self)
        self.form.move(10, 10)
        self.form.addItem(time.strftime("%d.%m.%Y"))
        self.form.addItem(time.strftime("%A, %d. %B %Y"))
        self.form.addItem(time.strftime("%d. %B %Y"))
        self.form.addItem(time.strftime("%d %m %Y"))
        self.form.addItem(time.strftime("%X"))
        self.form.addItem(time.strftime("%x"))
        self.form.addItem(time.strftime("%H:%M"))
        self.form.addItem(time.strftime("%A, %d. %B %Y %H:%M"))
        self.form.addItem(time.strftime("%d.%m.%Y %H:%M"))
        self.form.addItem(time.strftime("%d. %B %Y %H:%M"))

        self.form.activated[str].connect(self.handleChoice)

        self.ok = QtWidgets.QPushButton("Insert", self)
        self.ok.move(180, 10)

        self.cancel = QtWidgets.QPushButton("Cancel", self)
        self.cancel.move(180, 40)
        self.cancel.clicked.connect(self.Cancel)

        self.setGeometry(300, 300, 280, 70)

    def handleChoice(self, choice):
        global choiceStr
        choiceStr = choice

    def Cancel(self):
        self.close()


class ToolBarEdit(QtWidgets.QToolBar):
    sigPathChanged = QtCore.pyqtSignal(object)  # file path

    def __init__(self, textEdit):
        QtWidgets.QToolBar.__init__(self, 'Options')
        self.text = textEdit

        newAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-page.svg")),
            "New",
            self)
        newAction.setShortcut("Ctrl+N")
        newAction.setStatusTip("Create a new document from scratch.")
        newAction.triggered.connect(self.New)

        openAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-folder.svg")),
            "Open file",
            self)
        openAction.setStatusTip("Open existing document")
        openAction.setShortcut("Ctrl+O")
        openAction.triggered.connect(self.Open)

        saveAction = QtWidgets.QAction(QtGui.QIcon(
            iconfolder.join("fi-save.svg")), "Save", self)
        saveAction.setStatusTip("Save document")
        saveAction.setShortcut("Ctrl+S")
        saveAction.triggered.connect(self.Save)

        previewAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-results.svg")),
            "Page view",
            self)
        previewAction.setStatusTip("Preview page before printing")
        previewAction.setShortcut("Ctrl+Shift+P")
        previewAction.triggered.connect(self.PageView)

        findAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-page-search.svg")),
            "Find",
            self)
        findAction.setStatusTip("Find words in your document")
        findAction.setShortcut("Ctrl+F")
        findAction.triggered.connect(self.Find)

        cutAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-crop.svg")),
            "Cut to clipboard",
            self)
        cutAction.setStatusTip("Delete and copy text to clipboard")
        cutAction.setShortcut("Ctrl+X")
        cutAction.triggered.connect(self.Cut)

        copyAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-page-copy.svg")),
            "Copy to clipboard",
            self)
        copyAction.setStatusTip("Copy text to clipboard")
        copyAction.setShortcut("Ctrl+C")
        copyAction.triggered.connect(self.Copy)

        pasteAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-clipboard-notes.svg")),
            "Paste from clipboard",
            self)
        pasteAction.setStatusTip("Paste text from clipboard")
        pasteAction.setShortcut("Ctrl+V")
        pasteAction.triggered.connect(self.Paste)

        undoAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-arrow-left.svg")),
            "Undo last action",
            self)
        undoAction.setStatusTip("Undo last action")
        undoAction.setShortcut("Ctrl+Z")
        undoAction.triggered.connect(self.Undo)

        redoAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-arrow-right.svg")),
            "Redo last undone thing",
            self)
        redoAction.setStatusTip("Redo last undone thing")
        redoAction.setShortcut("Ctrl+Y")
        redoAction.triggered.connect(self.Redo)

        dtAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-clock.svg")),
            "Insert current date/time",
            self)
        dtAction.setStatusTip("Insert current date/time")
        dtAction.setShortcut("Ctrl+D")
        dtAction.triggered.connect(self.DateTime)

        printAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-print.svg")),
            "Print document",
            self)
        printAction.setStatusTip("Print document")
        printAction.setShortcut("Ctrl+P")
        printAction.triggered.connect(self.Print)

        self.addAction(newAction)
        self.addAction(openAction)
        self.addAction(saveAction)
        self.addSeparator()
        self.addAction(printAction)
        # self.toolbar.addAction(pdfAction)
        self.addAction(previewAction)
        self.addSeparator()
        self.addAction(findAction)
        self.addAction(cutAction)
        self.addAction(copyAction)
        self.addAction(pasteAction)
        self.addAction(undoAction)
        self.addAction(redoAction)
        self.addSeparator()
        self.addAction(dtAction)
        self.addSeparator()

    def New(self):
        self.text.clear()

    def Open(self):
        filename = dialogs.getOpenFileName()
        if filename:  # there is no fname in case the user canceled the menu
            f = open(filename, 'r')
            filedata = f.read()
            self.text.setText(filedata)
            self.sigPathChanged.emit(filename)
            f.close()

    def Save(self):
        filename = dialogs.getSaveFileName(
            filter="Text (*.txt);;PDF (*.pdf);;HTML (*.html)")
        if filename:
            ftype = filename.filetype()  # filename.split('.')[-1]
            if ftype.lower() == 'html':
                f = open(filename, 'w')
                filedata = self.text.toHtml()
                f.write(filedata)
                f.close()
            elif ftype.lower() == 'pdf':
                self.PDF(filename)
            else:  # text
                f = open(filename, 'w')
                filedata = self.text.toPlainText()
                f.write(filedata)
                f.close()
            self.sigPathChanged.emit(filename)

    def PageView(self):
        preview = QtPrintSupport.QPrintPreviewDialog()
        preview.paintRequested.connect(self.PaintPageView)
        preview.exec_()

    def Print(self):
        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.text.document().print_(dialog.printer())

    def PDF(self, name=None):
        printer = QtPrintSupport.QPrinter()
        printer.setOutputFormat(printer.NativeFormat)
        if name:
            printer.setOutputFileName(name)
            self.text.document().print_(printer)
        else:

            dialog = QtPrintSupport.QPrintDialog(printer)
            dialog.setOption(dialog.PrintToFile)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                self.text.document().print_(dialog.printer())

    def PaintPageView(self, printer):
        self.text.print_(printer)

    def Find(self):
        global f

        find = Find(self)
        find.show()

        def handleFind():

            f = find.te.toPlainText()
            # print(f)

            if cs is True and wwo is False:
                flag = QtGui.QTextDocument.FindBackward and QtGui.QTextDocument.FindCaseSensitively

            elif cs is False and wwo is False:
                flag = QtGui.QTextDocument.FindBackward

            elif cs is False and wwo is True:
                flag = QtGui.QTextDocument.FindBackward and QtGui.QTextDocument.FindWholeWords

            elif cs is True and wwo is True:
                flag = QtGui.QTextDocument.FindBackward and \
                    QtGui.QTextDocument.FindCaseSensitively and \
                    QtGui.QTextDocument.FindWholeWords

            self.text.find(f, flag)

        def handleReplace():
            f = find.te.toPlainText()
            r = find.rp.toPlainText()

            text = self.text.toPlainText()

            newText = text.replace(f, r)

            self.text.clear()
            self.text.append(newText)

        find.src.clicked.connect(handleFind)
        find.rpb.clicked.connect(handleReplace)

    def Undo(self):
        self.text.undo()

    def Redo(self):
        self.text.redo()

    def Cut(self):
        self.text.cut()

    def Copy(self):
        self.text.copy()

    def Paste(self):
        self.text.paste()

    def DateTime(self):
        date = Date(self)
        date.show()
        date.ok.clicked.connect(self.insertDate)

    def insertDate(self):
        global choiceStr
        self.text.append(choiceStr)


class ToolBarInsert(QtWidgets.QToolBar):

    def __init__(self, textEdit):
        QtWidgets.QToolBar.__init__(self, 'insert')
        self._nimages = 0
        self.text = textEdit
        self.text.setAcceptRichText(True)

        imageAction = QtWidgets.QAction(QtGui.QIcon(
            iconfolder.join("fi-photo.svg")), "Add an image.", self)
        imageAction.setShortcut("Ctrl+Shift+I")
        imageAction.triggered.connect(self.insertImage)

        snippedAction = QtWidgets.QAction(QtGui.QIcon(
            iconfolder.dirname().join("snipping.svg")), "Snipping tool", self)
        snippedAction.triggered.connect(self.insertSnipped)

        self.addAction(snippedAction)
        self.addAction(imageAction)

    def insertSnipped(self):
        s = SnippingArea()
        s.exec_()
        self._insertQImage(s.img.toImage())

    def insertImage(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(
            caption="Select an image", directory=".",
            filter="Image Files (*.png *.jpg *.bmp)")
        image = QtGui.QImage(filename[0])
        # Error if unloadable
        if image.isNull():
            popup = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical,
                                          "Image load error",
                                          "Could not load image file!",
                                          QtWidgets.QMessageBox.Ok,
                                          self)
            popup.show()
        else:
            self._insertQImage(image)

    def _insertQImage(self, image, hmax=500):
        self._nimages += 1
        cursor = self.text.textCursor()
        doc = self.text.document()
        url = QtCore.QUrl("mydata://image%i.png" % self._nimages)
        doc.addResource(doc.ImageResource,
                        url,
                        QtCore.QVariant(image))
        f = QtGui.QTextImageFormat()
        w, h = image.width(), image.height()

        if h > hmax:
            a = h / hmax
            w = w / a
            h = hmax
        f.setWidth(w)
        f.setHeight(h)
        f.setName(url.toString())
        cursor.insertImage(f)


class ToolBarFont(QtWidgets.QToolBar):

    def __init__(self, textEdit):
        QtWidgets.QToolBar.__init__(self, 'Font')
        self.text = textEdit

        self.fontFamily = QtWidgets.QFontComboBox(self)
        self.fontFamily.currentFontChanged.connect(self.FontFamily)

        fontSize = QtWidgets.QComboBox(self)
        fontSize.setEditable(True)
        fontSize.setMinimumContentsLength(3)
        fontSize.activated.connect(self.FontSize)
        flist = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 32, 36, 40, 44, 48,
                 54, 60, 66, 72, 80, 88, 96]

        for i in flist:
            fontSize.addItem(str(i))

        space1 = QtWidgets.QLabel("  ", self)
        space2 = QtWidgets.QLabel(" ", self)

        self.addWidget(self.fontFamily)
        self.addWidget(space1)
        self.addWidget(fontSize)
        self.addWidget(space2)

    def FontFamily(self, font):
        font = QtGui.QFont(self.fontFamily.currentFont())
        self.text.setCurrentFont(font)

    def FontSize(self, fsize):
        size = (int(fsize))
        self.text.setFontPointSize(size)


class ToolBarFormat(QtWidgets.QToolBar):

    def __init__(self, textEdit):
        QtWidgets.QToolBar.__init__(self, 'Format')
        self.text = textEdit

        fontColor = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-text-color.svg")),
            "Change font color",
            self)
        fontColor.triggered.connect(self.FontColor)

        boldAction = QtWidgets.QAction(QtGui.QIcon(
            iconfolder.join("fi-bold.svg")), "Bold", self)
        boldAction.triggered.connect(self.Bold)

        italicAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-italic.svg")),
            "Italic",
            self)
        italicAction.triggered.connect(self.Italic)

        underlAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-underline.svg")),
            "Underline",
            self)
        underlAction.triggered.connect(self.Underl)

        alignLeft = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-align-left.svg")),
            "Align left",
            self)
        alignLeft.triggered.connect(self.alignLeft)

        alignCenter = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-align-center.svg")),
            "Align center",
            self)
        alignCenter.triggered.connect(self.alignCenter)

        alignRight = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-align-right.svg")),
            "Align right",
            self)
        alignRight.triggered.connect(self.alignRight)

        alignJustify = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-align-justify.svg")),
            "Align justify",
            self)
        alignJustify.triggered.connect(self.alignJustify)

        indentAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-indent-more.svg")),
            "Indent Area",
            self)
        indentAction.setShortcut("Ctrl+Tab")
        indentAction.triggered.connect(self.Indent)

        dedentAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-indent-less.svg")),
            "Dedent Area",
            self)
        dedentAction.setShortcut("Shift+Tab")
        dedentAction.triggered.connect(self.Dedent)

        backColor = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-background-color.svg")),
            "Change background color",
            self)
        backColor.triggered.connect(self.FontBackColor)

        bulletAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-list-bullet.svg")),
            "Insert Bullet List",
            self)
        bulletAction.triggered.connect(self.BulletList)

        numberedAction = QtWidgets.QAction(
            QtGui.QIcon(
                iconfolder.join("fi-list-number.svg")),
            "Insert Numbered List",
            self)
        numberedAction.triggered.connect(self.NumberedList)

        self.addAction(fontColor)
        self.addAction(backColor)

        self.addSeparator()

        self.addAction(boldAction)
        self.addAction(italicAction)
        self.addAction(underlAction)

        self.addSeparator()

        self.addAction(alignLeft)
        self.addAction(alignCenter)
        self.addAction(alignRight)
        self.addAction(alignJustify)

        self.addSeparator()

        self.addAction(indentAction)
        self.addAction(dedentAction)
        self.addAction(bulletAction)
        self.addAction(numberedAction)

    def FontColor(self):
        c = QtWidgets.QColorDialog.getColor()
        self.text.setTextColor(c)

    def FontBackColor(self):
        c = QtWidgets.QColorDialog.getColor()
        self.text.setTextBackgroundColor(c)

    def Bold(self):
        w = self.text.fontWeight()
        if w == 50:
            self.text.setFontWeight(QtGui.QFont.Bold)
        elif w == 75:
            self.text.setFontWeight(QtGui.QFont.Normal)

    def Italic(self):
        i = self.text.fontItalic()

        if i == False:
            self.text.setFontItalic(True)
        elif i == True:
            self.text.setFontItalic(False)

    def Underl(self):
        ul = self.text.fontUnderline()

        if ul == False:
            self.text.setFontUnderline(True)
        elif ul == True:
            self.text.setFontUnderline(False)

#   def lThrough(self):
#       lt = QtGui.QFont.style()
        # print(lt)

    def alignLeft(self):
        self.text.setAlignment(Qt.AlignLeft)

    def alignRight(self):
        self.text.setAlignment(Qt.AlignRight)

    def alignCenter(self):
        self.text.setAlignment(Qt.AlignCenter)

    def alignJustify(self):
        self.text.setAlignment(Qt.AlignJustify)

    def Indent(self):
        # TODO: doesn't work
        tab = "\t"
        cursor = self.text.textCursor()

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(end)
        cursor.movePosition(cursor.EndOfLine)
        end = cursor.position()

        cursor.setPosition(start)
        cursor.movePosition(cursor.StartOfLine)
        start = cursor.position()

        while cursor.position() < end:
            global var
            cursor.movePosition(cursor.StartOfLine)
            cursor.insertText(tab)
            cursor.movePosition(cursor.Down)
            end += len(tab)

            '''if cursor.position() == end:
                var +=1

            if var == 2:
                break'''

    def Dedent(self):
        # TODO: doesn't work

        tab = "\t"
        cursor = self.text.textCursor()

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(end)
        cursor.movePosition(cursor.EndOfLine)
        end = cursor.position()

        cursor.setPosition(start)
        cursor.movePosition(cursor.StartOfLine)
        start = cursor.position()

        while cursor.position() < end:
            global var

            cursor.movePosition(cursor.StartOfLine)
            cursor.deleteChar()
            cursor.movePosition(cursor.EndOfLine)
            cursor.movePosition(cursor.Down)
            end -= len(tab)

            '''if cursor.position() == end:
                var +=1

            if var == 2:
                break'''

    def BulletList(self):
        self.text.textCursor().insertList(QtGui.QTextListFormat.ListDisc)

    def NumberedList(self):
        self.text.textCursor().insertList(QtGui.QTextListFormat.ListDecimal)
