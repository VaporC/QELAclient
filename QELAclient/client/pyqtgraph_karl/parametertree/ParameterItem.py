from ..Qt import QtGui, QtCore
from ..python2_3 import asUnicode
import os, weakref, re

class ParameterItem(QtGui.QTreeWidgetItem):
    """
    Abstract ParameterTree item. 
    Used to represent the state of a Parameter from within a ParameterTree.
    
    - Sets first column of item to name
    - generates context menu if item is renamable or removable
    - handles child added / removed events
    - provides virtual functions for handling changes from parameter
    
    For more ParameterItem types, see ParameterTree.parameterTypes module.
    """
    
    def __init__(self, param, depth=0):
        title = param.opts.get('title', None)
        if title is None:
            title = param.name()
        QtGui.QTreeWidgetItem.__init__(self, [title, ''])

        self.param = param
        self.param.registerItem(self)  ## let parameter know this item is connected to it (for debugging)
        self.depth = depth
        
        param.sigValueChanged.connect(self.valueChanged)
        param.sigChildAdded.connect(self.childAdded)
        param.sigChildRemoved.connect(self.childRemoved)
        param.sigNameChanged.connect(self.nameChanged)
        param.sigLimitsChanged.connect(self.limitsChanged)
        param.sigDefaultChanged.connect(self.defaultChanged)
        param.sigOptionsChanged.connect(self.optsChanged)
        param.sigParentChanged.connect(self.parentChanged)
        
        opts = param.opts
        
        ## Generate context menu for renaming/removing parameter
        self.contextMenu = QtGui.QMenu()
        self.contextMenu.addSeparator()
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if opts.get('renamable', False):
            if param.opts.get('title', None) is not None:
                raise Exception("Cannot make parameter with both title != None and renamable == True.")
            flags |= QtCore.Qt.ItemIsEditable
            self.contextMenu.addAction('Rename').triggered.connect(self.editName)
        if opts.get('removable', False):
            self.contextMenu.addAction("Remove").triggered.connect(self.requestRemove)
        
        ## handle movable / dropEnabled options
        if opts.get('movable', False):
            flags |= QtCore.Qt.ItemIsDragEnabled
        if opts.get('dropEnabled', False):
            flags |= QtCore.Qt.ItemIsDropEnabled
        self.setFlags(flags)
        
        ## flag used internally during name editing
        self.ignoreNameColumnChange = False
    
        menuitems = opts.get('addToContextMenu', None)
        if menuitems:
            for i in menuitems:
                try:
                    self.contextMenu.addMenu(i)
                except TypeError:
                    self.contextMenu.addAction(i)
            #needs to save items, otherwise they are removed from contextMenu
            self._contextMenuItems = opts.pop('addToContextMenu')
        # SLIDING
        if opts.get('sliding', False):
            self.controls = QtGui.QWidget()
            btnlayout = QtGui.QVBoxLayout()
            btnlayout.setContentsMargins(0, 0, 0, 0)
            btnlayout.setSpacing(0)
            self.controls.setLayout(btnlayout)
            slideBtnUp = QtGui.QPushButton()
            slideBtnDown = QtGui.QPushButton()

            for btn in (slideBtnUp, slideBtnDown):
                btn.setFixedWidth(10)
                btn.setFixedHeight(10)
                btnlayout.addWidget(btn)

            slideBtnUp.setIcon(
                QtGui.QApplication.style().standardIcon(
                    QtGui.QStyle.SP_ArrowUp))
            slideBtnDown.setIcon(
                QtGui.QApplication.style().standardIcon(
                    QtGui.QStyle.SP_ArrowDown))
            slideBtnUp.clicked.connect(
                lambda: self.slideChild(-1))  # param.slide(-1))
            slideBtnDown.clicked.connect(
                lambda: self.slideChild(1))  # param.slide(1))

        # DUPLICABILITY
        if opts.get('duplicatable', False):
            self.contextMenu.addAction(
                "Duplicate").triggered.connect(param.duplicate)
        #if opts.get('type') == 'group':
         #   self.updateDepth(depth)
        # ICON
        iconpath = opts.get('icon', False)
        if iconpath:
            i = QtGui.QIcon(iconpath)
            self.setIcon(0, i)
        # TOOLTIP
        # TODO: test
        tip = opts.get('tip', False)
        if tip:
            self.setToolTip(0, tip)
        # KEYBOARD SHORTCUT
        self.key = None
        self.setShortcut(opts.get('key'), opts.get('keyParent'))

    #ADDED
    def setShortcut(self, key, parent):
        if key:
            k = QtGui.QShortcut(parent)
            if not isinstance(key, QtGui.QKeySequence):
                key = QtGui.QKeySequence(key)
            k.setKey(QtGui.QKeySequence(key))
            k.setContext(QtCore.Qt.ApplicationShortcut)
            try:
                # for ActionParameter
                k.activated.connect(self.param.activate)
            except AttributeError:
                # toggle
                k.activated.connect(
                    lambda: self.param.setValue(
                        not self.param.value()))
            self.key = k

    #ADDED
    def slideChild(self, nPos):
        c = self.treeWidget().currentItem()
        for n in range(self.childCount()):
            if c == self.child(n):
                c.param.slide(nPos)
                cnew = self.child(n + nPos)
                #TODO: c has no parent any more
                return self.treeWidget().setCurrentItem(cnew, 0)


    def valueChanged(self, param, val):
        ## called when the parameter's value has changed
        pass
    
    def isFocusable(self):
        """Return True if this item should be included in the tab-focus order"""
        return False
        
    def setFocus(self):
        """Give input focus to this item.
        Can be reimplemented to display editor widgets, etc.
        """
        pass
    
    def focusNext(self, forward=True):
        """Give focus to the next (or previous) focusable item in the parameter tree"""
        self.treeWidget().focusNext(self, forward=forward)
        
    def treeWidgetChanged(self):
        """Called when this item is added or removed from a tree.
        Expansion, visibility, and column widgets must all be configured AFTER 
        the item is added to a tree, not during __init__.
        """
        self.setHidden(not self.param.opts.get('visible', True))
        self.setExpanded(self.param.opts.get('expanded', True))
 
        if self.param.opts.get('sliding', False):
            t = self.treeWidget()
            i = t.itemWidget(self, 0)
            if i is None:
                t.setItemWidget(self, 0, self.controls)
                # move the name a bit
                # if self.text(0)
                # self._setTextSliding(0,self.text(0))
            else:
                # TODO: does this work??
                i.insertWidget(0, self.controls)

    def childAdded(self, param, child, pos):
        item = child.makeTreeItem(depth=self.depth+1)
        self.insertChild(pos, item)
        item.treeWidgetChanged()
        
        for i, ch in enumerate(child):
            item.childAdded(child, ch, i)
        
    def childRemoved(self, param, child):
        for i in range(self.childCount()):
            item = self.child(i)
            if item.param is child:
                self.takeChild(i)
                break
                
    def parentChanged(self, param, parent):
        ## called when the parameter's parent has changed.
        pass
                
    def contextMenuEvent(self, ev):
       # if not self.param.opts.get('removable', False) and not self.param.opts.get('renamable', False):
       #     return
        self.contextMenu.popup(ev.globalPos())
        
    def columnChangedEvent(self, col):
        """Called when the text in a column has been edited (or otherwise changed).
        By default, we only use changes to column 0 to rename the parameter.
        """
        if col == 0  and (self.param.opts.get('title', None) is None):
            if self.ignoreNameColumnChange:
                return
            try:
                newName = self.param.setName(asUnicode(self.text(col)))
            except Exception:
                self.setText(0, self.param.name())
                raise
                
            try:
                self.ignoreNameColumnChange = True
                self.nameChanged(self, newName)  ## If the parameter rejects the name change, we need to set it back.
            finally:
                self.ignoreNameColumnChange = False
                
    def nameChanged(self, param, name):
        ## called when the parameter's name has changed.
        if self.param.opts.get('title', None) is None:
            self.setText(0, name)
    
    def limitsChanged(self, param, limits):
        """Called when the parameter's limits have changed"""
        pass
    
    def defaultChanged(self, param, default):
        """Called when the parameter's default value has changed"""
        pass

    def optsChanged(self, param, opts):
        """Called when any options are changed that are not
        name, value, default, or limits"""
        #print opts
        if 'visible' in opts:
            self.setHidden(not opts['visible'])
        
    def editName(self):
        self.treeWidget().editItem(self, 0)
        
    def selected(self, sel):
        """Called when this item has been selected (sel=True) OR deselected (sel=False)"""
        pass

    def requestRemove(self):
        ## called when remove is selected from the context menu.
        ## we need to delay removal until the action is complete
        ## since destroying the menu in mid-action will cause a crash.
        QtCore.QTimer.singleShot(0, self.param.remove)

    ## for python 3 support, we need to redefine hash and eq methods.
    def __hash__(self):
        return id(self)

    def __eq__(self, x):
        return x is self
