# -*- coding: utf-8 -*-

# Copyright (C) 2013 Michael Hogg

# This file is part of BMDanalyse - See LICENSE.txt for information on usage and redistribution

import os, sys, matplotlib, matplotlib.pyplot
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.widgets.GraphicsLayoutWidget import GraphicsLayoutWidget
from ViewBoxCustom import MultiRoiViewBox

absDirPath = os.path.dirname(__file__)  
    
class MainWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
    
        QtGui.QMainWindow.__init__(self, parent) 
        self.setupUserInterface() 
    
    def setupUserInterface(self):
    
        frame = QtGui.QFrame()
        frameLayout = QtGui.QHBoxLayout() 
        frame.setLayout(frameLayout)
        frame.setLineWidth(0)
        frame.setFrameStyle(QtGui.QFrame.Panel)
        frameLayout.setContentsMargins(0,0,5,0)
 
        self.viewMain = GraphicsLayoutWidget() 
        self.viewMain.setMinimumSize(200,200)
        self.vb = MultiRoiViewBox(lockAspect=True,enableMenu=True)
        self.viewMain.addItem(self.vb)
        self.vb.disableAutoRange()
        self.setCentralWidget(self.viewMain)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
