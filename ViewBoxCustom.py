# -*- coding: utf-8 -*-

# Copyright (C) 2013 Michael Hogg

# This file is part of BMDanalyse - See LICENSE.txt for information on usage and redistribution

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore,QtGui
import numpy as np
from ROI import ROI, RectROIcustom, PolyLineROIcustom
from pyqtgraph.exporters import ImageExporter
from PIL import Image
import matplotlib
import pickle
import pyqtgraph.functions as fn
import types

__all__=['MultiRoiViewBox']

class MultiRoiViewBox(pg.ViewBox):

    sigROIchanged = QtCore.Signal(object)

    def __init__(self,parent=None,border=None,lockAspect=False,enableMouse=True,invertY=False,enableMenu=True,name=None):
        pg.ViewBox.__init__(self,parent,border,lockAspect,enableMouse,invertY,enableMenu,name)
        
        self.rois = []
        self.currentROIindex = None
        self.img         = None
        self.menu        = None
        self.menu        = self.getMenu(None)       
        self.drawROImode = False
        self.drawingROI  = None
        
    def getContextMenus(self,ev):
        return None
        
    def raiseContextMenu(self, ev):
        if not self.menuEnabled(): return
        menu = self.getMenu(ev)
        pos  = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        
    def export(self):
        self.exp = ImageExporter(self)
        self.exp.export()
        
    def mouseClickEvent(self, ev):
        if self.drawROImode:
            ev.accept()
            self.drawPolygonRoi(ev)            
        elif ev.button() == QtCore.Qt.RightButton and self.menuEnabled():
            ev.accept()
            self.raiseContextMenu(ev) 
            
    def addPolyRoiRequest(self):
        """Function to add a Polygon ROI"""
        self.drawROImode = True
        for roi in self.rois:        
           roi.setActive(False)           

    def endPolyRoiRequest(self):
        self.drawROImode = False  # Deactivate drawing mode
        self.drawingROI  = None   # No roi being drawn, so set to None
        for r in self.rois:
            r.setActive(True)
            
    def addPolyLineROI(self,handlePositions):
        roi = PolyLineROIcustom(handlePositions=handlePositions,removable=True)
        roi.setName('ROI-%i'% self.getROIid())
        self.addItem(roi)                      # Add roi to viewbox
        self.rois.append(roi)                  # Add to list of rois
        self.selectROI(roi)
        self.sortROIs()  
        self.setCurrentROIindex(roi)  
        roi.translatable = True   
        roi.setActive(True)      
        for seg in roi.segments:
            seg.setSelectable(True)
        for h in roi.handles:
            h['item'].setSelectable(True)
        # Setup signals
        roi.sigClicked.connect(self.selectROI)
        roi.sigRegionChanged.connect(self.roiChanged)
        roi.sigRemoveRequested.connect(self.removeROI)
        roi.sigCopyRequested.connect(self.copyROI)
        roi.sigSaveRequested.connect(self.saveROI)            

    def drawPolygonRoi(self,ev):
        "Function to draw a polygon ROI"
        roi = self.drawingROI
        pos = self.mapSceneToView(ev.scenePos())
        
        if ev.button() == QtCore.Qt.LeftButton:
            if roi is None:            
                roi = PolyLineROIcustom(removable = False)
                roi.setName('ROI-%i'% self.getROIid()) # Do this before self.selectROIs(roi)
                self.drawingROI = roi                  
                self.addItem(roi)                      # Add roi to viewbox
                self.rois.append(roi)                  # Add to list of rois
                self.selectROI(roi)
                self.sortROIs()  
                self.setCurrentROIindex(roi)                
                roi.translatable = False 
                roi.addFreeHandle(pos)
                roi.addFreeHandle(pos)
                h = roi.handles[-1]['item']
                h.scene().sigMouseMoved.connect(h.movePoint)
            else:
                h = roi.handles[-1]['item']
                h.scene().sigMouseMoved.disconnect()           
                roi.addFreeHandle(pos)
                h = roi.handles[-1]['item']
                h.scene().sigMouseMoved.connect(h.movePoint)                
            # Add a segment between the handles
            roi.addSegment(roi.handles[-2]['item'],roi.handles[-1]['item'])
            # Set segment and handles to non-selectable
            seg = roi.segments[-1]
            seg.setSelectable(False)
            for h in seg.handles:
                h['item'].setSelectable(False)
                
        elif (ev.button() == QtCore.Qt.MiddleButton) or \
             (ev.button() == QtCore.Qt.RightButton and (roi==None or len(roi.segments)<3)):
            if roi!=None:
                # Remove handle and disconnect from scene
                h = roi.handles[-1]['item']
                h.scene().sigMouseMoved.disconnect()
                roi.removeHandle(h)
                # Removed roi from viewbox
                self.removeItem(roi)
                self.rois.pop(self.currentROIindex)
                self.setCurrentROIindex(None)
            # Exit ROI drawing mode
            self.endPolyRoiRequest()

        elif ev.button() == QtCore.Qt.RightButton:
            # Remove last handle
            h = roi.handles[-1]['item']
            h.scene().sigMouseMoved.disconnect()  
            roi.removeHandle(h)
            # Add segment to close ROI
            roi.addSegment(roi.handles[-1]['item'],roi.handles[0]['item'])
            # Setup signals
            roi.sigClicked.connect(self.selectROI)
            roi.sigRegionChanged.connect(self.roiChanged)
            roi.sigRemoveRequested.connect(self.removeROI)
            roi.sigCopyRequested.connect(self.copyROI)
            roi.sigSaveRequested.connect(self.saveROI)
            # Re-activate mouse clicks for all roi, segments and handles
            roi.removable    = True
            roi.translatable = True  
            for seg in roi.segments:
                seg.setSelectable(True)
            for h in roi.handles:
                h['item'].setSelectable(True)
            # Exit ROI drawing mode
            self.endPolyRoiRequest()                
                
    def getMenu(self,event):
        if self.menu is None:
            self.menu          = QtGui.QMenu()
            # Submenu to add ROIs
            self.submenu       = QtGui.QMenu("Add ROI",self.menu)
            self.addROIRectAct = QtGui.QAction("Rectangular",  self.submenu)
            self.addROIPolyAct = QtGui.QAction("Polygon",  self.submenu)
            self.addROIRectAct.triggered.connect(self.addROI)
            self.addROIPolyAct.triggered.connect(self.addPolyRoiRequest)    
            self.submenu.addAction(self.addROIRectAct)
            self.submenu.addAction(self.addROIPolyAct)
            
            self.loadImageAct = QtGui.QAction("Load image", self.menu)
            self.loadImageAct.triggered.connect(self.loadImage)
            self.loadROIAct  = QtGui.QAction("Load ROI", self.menu)
            self.viewAll     = QtGui.QAction("View All", self.menu)
            self.viewAll.triggered[()].connect(self.autoRange)
            
            self.menu.addAction(self.loadImageAct)
            self.menu.addAction(self.viewAll)
            self.menu.addSeparator()
            self.menu.addMenu(self.submenu)
            self.menu.addAction(self.loadROIAct)
            
        # Update action event. This enables passing of the event to the fuction connected to the
        # action i.e.  event will be passed to self.addRoiRequest when a Rectangular ROI is clicked
        #self.addROIRectAct.updateEvent(event)
        #self.addROIPolyAct.updateEvent(event)
        return self.menu  
        
    def setCurrentROIindex(self,roi=None):
        """ Use this function to change currentROIindex value to ensure a signal is emitted"""
        if roi==None: self.currentROIindex = None
        else:         self.currentROIindex = self.rois.index(roi)
        self.sigROIchanged.emit(roi)  

    def roiChanged(self,roi):
        self.sigROIchanged.emit(roi) 

    def getCurrentROIindex(self):
        return self.currentROIindex    
    
    def selectROI(self,roi):
        """ Selection control of ROIs """
        # If no ROI is currently selected (currentROIindex is None), select roi
        if self.currentROIindex==None:
            roi.setSelected(True)
            self.setCurrentROIindex(roi)
        # If an ROI is already selected...
        else:
            roiSelected = self.rois[self.currentROIindex]
            roiSelected.setSelected(False) 
            # If a different roi is already selected, then select roi 
            if self.currentROIindex != self.rois.index(roi):
                self.setCurrentROIindex(roi)
                roi.setSelected(True)
            # If roi is already selected, then unselect
            else: 
                self.setCurrentROIindex(None)
        
    def addRoiRequest(self,ev):
        """ Function to addROI at an event screen position """
        # Get position
        pos  = self.mapSceneToView(ev.scenePos())        
        xpos = pos.x()
        ypos = pos.y()
        # Shift down by size
        xr,yr = self.viewRange()
        xsize  = 0.25*(xr[1]-xr[0])
        ysize  = 0.25*(yr[1]-yr[0])
        xysize = min(xsize,ysize)
        if xysize==0: xysize=100       
        ypos -= xysize
        # Create ROI
        xypos = (xpos,ypos)
        self.addROI(pos=xypos)
        
    def addROI(self,pos=None,size=None,angle=0.0):
        """ Add an ROI to the ViewBox """    
        xr,yr = self.viewRange()
        if pos is None:
            posx = xr[0]+0.05*(xr[1]-xr[0])
            posy = yr[0]+0.05*(yr[1]-yr[0])
            pos  = [posx,posy]
        if size is None:
            xsize  = 0.25*(xr[1]-xr[0])
            ysize  = 0.25*(yr[1]-yr[0])
            xysize = min(xsize,ysize)
            if xysize==0: xysize=100
            size = [xysize,xysize]  
        roi = RectROIcustom(pos,size,angle,removable=True,pen=(255,0,0))
        # Setup signals
        roi.setName('ROI-%i'% self.getROIid()) 
        roi.sigClicked.connect(self.selectROI)
        roi.sigRegionChanged.connect(self.roiChanged)
        roi.sigRemoveRequested.connect(self.removeROI)
        roi.sigCopyRequested.connect(self.copyROI)
        roi.sigSaveRequested.connect(self.saveROI)
        # Keep track of rois
        self.addItem(roi)
        self.rois.append(roi)
        self.selectROI(roi)
        self.sortROIs()  
        self.setCurrentROIindex(roi)

    def sortROIs(self):
        """ Sort self.rois by roi name and adjust self.currentROIindex as necessary """
        if len(self.rois)==0: return 
        if self.currentROIindex==None:
            self.rois.sort()  
        else:
            roiCurrent = self.rois[self.currentROIindex]
            self.rois.sort()  
            self.currentROIindex = self.rois.index(roiCurrent)
    
    def getROIid(self):
        """ Get available and unique number for ROI name """
        nums = [ int(roi.name.split('-')[-1]) for roi in self.rois if roi.name!=None ]
        nid  = 1
        if len(nums)>0: 
            while(True):
                if nid not in nums: break
                nid+=1
        return nid
        
    def copyROI(self,offset=0.0):
        """ Copy current ROI. Offset from original for visibility """
        if self.currentROIindex!=None:
            osFract = 0.05              
            roi     = self.rois[self.currentROIindex]
            # For rectangular ROI, offset by a fraction of the rotated size
            if type(roi)==RectROIcustom: 
                roiState = roi.getState()
                pos      = roiState['pos']
                size     = roiState['size']
                angle    = roiState['angle']
                dx,dy    = np.array(size)*osFract               
                ang      = np.radians(angle)
                cosa     = np.cos(ang)
                sina     = np.sin(ang)
                dxt      = dx*cosa - dy*sina
                dyt      = dx*sina + dy*cosa
                offset   = QtCore.QPointF(dxt,dyt) 
                self.addROI(pos+offset,size,angle)
            # For a polyline ROI, offset by a fraction of the bounding rectangle
            if type(roi)==PolyLineROIcustom:                             
                br        = roi.shape().boundingRect()
                size      = np.array([br.width(),br.height()])
                osx,osy   = size * osFract
                offset    = QtCore.QPointF(osx,osy)                
                hps       = [i[-1] for i in roi.getSceneHandlePositions(index=None)]                
                hpsOffset = [self.mapSceneToView(hp)+offset for hp in hps] 
                self.addPolyLineROI(hpsOffset)
     
    def saveROI(self):
        """ Save the highlighted ROI to file """    
        if self.currentROIindex!=None:
            roi = self.rois[self.currentROIindex]
            fileName = QtGui.QFileDialog.getSaveFileName(None,self.tr("Save ROI"),QtCore.QDir.currentPath(),self.tr("ROI (*.roi)"))
            # Fix for PyQt/PySide compatibility. PyQt returns a QString, whereas PySide returns a tuple (first entry is filename as string)        
            if isinstance(fileName,types.TupleType): fileName = fileName[0]
            if hasattr(QtCore,'QString') and isinstance(fileName, QtCore.QString): fileName = str(fileName)            
            if not fileName=='':
                if type(roi)==RectROIcustom:
                    roiState = roi.saveState()
                    roiState['type']='RectROIcustom'
                elif type(roi)==PolyLineROIcustom: 
                    roiState = {}
                    hps   = [self.mapSceneToView(i[-1]) for i in roi.getSceneHandlePositions(index=None)]                                                      
                    hps   = [[hp.x(),hp.y()] for hp in hps]
                    roiState['type']='PolyLineROIcustom'    
                    roiState['handlePositions'] = hps
                pickle.dump( roiState, open( fileName, "wb" ) )
                          
    def loadROI(self):
        """ Load a previously saved ROI from file """
        fileNames = QtGui.QFileDialog.getOpenFileNames(None,self.tr("Load ROI"),QtCore.QDir.currentPath(),self.tr("ROI (*.roi)"))
        # Fix for PyQt/PySide compatibility. PyQt returns a QString, whereas PySide returns a tuple (first entry is filename as string)        
        if isinstance(fileNames,types.TupleType): fileNames = fileNames[0]
        if hasattr(QtCore,'QStringList') and isinstance(fileNames, QtCore.QStringList): fileNames = [str(i) for i in fileNames]
        if len(fileNames)>0:
            for fileName in fileNames:
                if fileName!='':
                    roiState = pickle.load( open(fileName, "rb") )
                    if roiState['type']=='RectROIcustom':
                        self.addROI(roiState['pos'],roiState['size'],roiState['angle'])    
                    elif roiState['type']=='PolyLineROIcustom':
                        self.addPolyLineROI(roiState['handlePositions'])
            
    def removeROI(self):
        """ Delete the highlighted ROI """
        if self.currentROIindex!=None:
            roi = self.rois[self.currentROIindex]
            self.rois.pop(self.currentROIindex)
            self.removeItem(roi)  
            self.setCurrentROIindex(None) 

    def loadImage(self):
        fileName = QtGui.QFileDialog.getOpenFileName(None, self.tr("Load image"), QtCore.QDir.currentPath())    
        if fileName!='':
            try:
                imgarr = np.array(Image.open(str(fileName)))
                imgarr = imgarr.swapaxes(0,1)
                if   imgarr.ndim==2: imgarr = imgarr[:,::-1]
                elif imgarr.ndim==3: imgarr = imgarr[:,::-1,:]                   
                self.imgarr = imgarr
            except:
                pass
            else:
                self.enableAutoRange()
                self.showImage(self.imgarr)
                self.disableAutoRange()
       
    def showImage(self,arr):
        if arr is None: 
            self.img = None
            return
        if self.img==None: 
            self.img = pg.ImageItem(arr,autoRange=False,autoLevels=False)
            self.addItem(self.img)      
        self.img.setImage(arr,autoLevels=False)
        
