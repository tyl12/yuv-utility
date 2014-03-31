#!/usr/bin/python
import sys
import os
import re
import shutil
import subprocess
import datetime
import traceback

import numpy as np
import cv2
from cv2 import cv
import yuvdecoder

from PyQt4 import QtGui
from PyQt4 import QtCore

#sys.path.append('../..')
COLOR_LIST = yuvdecoder.YUVDecoder.get_color_list()

gControlDurationMs = 2000

def cur_file_dir():
    return os.path.dirname(os.path.realpath(__file__))

def centerWindow(winobj):
    screen = QtGui.QDesktopWidget().screenGeometry()
    size = winobj.geometry()
    winobj.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)

class sliderPanel(QtGui.QWidget):
    def __init__(self, parent, yuvfile, color, imgwidth, imgheight):
        super(sliderPanel, self).__init__()
        self.parent = parent
        self.yuvfile = yuvfile
        self.color = color
        self.imgwidth = imgwidth
        self.imgheight = imgheight

        self.initUI()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()
        #init timer
        self.timer = QtCore.QBasicTimer()
        self.installEventFilter(self)

    def initUI(self):
        bys = os.path.getsize(self.yuvfile)
        bpp = yuvdecoder.YUVDecoder.getbpp(self.color) #bit per pixel

        self.totalFrameNumber = int(bys*8/bpp/(self.imgwidth*self.imgheight))
        self.slider=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.totalFrameNumber-1)
        print "total frame number:", self.totalFrameNumber

        self.imagelb=QtGui.QLabel()
        self.imagelb.setAlignment(QtCore.Qt.AlignLeft)
        self.connect(self.slider, QtCore.SIGNAL('valueChanged(int)'), self.display)

        self.prevDirection = QtGui.QPushButton('Prev')
        self.nextDirection = QtGui.QPushButton('Next')
        self.play = QtGui.QPushButton('Play')
        self.play.setText("Play")
        self.connect(self.prevDirection, QtCore.SIGNAL('clicked()'), self.click_prev)
        self.connect(self.nextDirection, QtCore.SIGNAL('clicked()'), self.click_next)
        self.connect(self.play, QtCore.SIGNAL('clicked()'), self.click_play)

        self.hlay = QtGui.QHBoxLayout()
        self.hlay.addWidget(self.prevDirection)
        self.hlay.addWidget(self.nextDirection)
        self.hlay.addWidget(self.play)

        self.vlay = QtGui.QVBoxLayout()
        self.vlay.addWidget(self.imagelb)
        self.vlay.addWidget(self.slider)
        self.vlay.addLayout(self.hlay)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addLayout(self.vlay)
        self.setLayout(self.layout)

        self.setWindowModality(QtCore.Qt.ApplicationModal) #should before show
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.display(0) #show first frame for first view

    def click_prev(self):
        idx=self.slider.value()
        if idx > 0:
            idx -= 1
            self.slider.setValue(idx)
        return

    def click_next(self):
        idx=self.slider.value()
        if idx < self.totalFrameNumber-1:
            idx += 1
            self.slider.setValue(idx)
        return

    def eventFilter(self, obj, event):
        if (event.type() == QtCore.QEvent.WindowActivate) and ( not self.timer.isActive()):
            print "Enable timer"
            self.timer.start(gControlDurationMs, self)
        elif (event.type() == QtCore.QEvent.WindowDeactivate) and ( self.timer.isActive()):
            print "Disable timer"
            self.timer.stop()
        return QtGui.QMainWindow.eventFilter(self, obj, event)

    def timerEvent(self, event):
        self.click_next()
        if self.slider.value() == self.totalFrameNumber-1:
            self.click_play() #stop when encounter EOF

    def click_play(self):
        if self.play.text() == "Play":
            self.play.setText("Stop")
            self.timer.start(gControlDurationMs, self)
        else:
            self.play.setText("Play")
            self.timer.stop()

    def display(self, index):
        print "display file: %s, index: %s" % (self.yuvfile,index)
        image = QtGui.QImage()
        screen = QtGui.QDesktopWidget().screenGeometry()

        row = self.imgheight
        col = self.imgwidth
        color = self.color
        f = self.yuvfile

        decoder = yuvdecoder.YUVDecoder(f, color, row, col)
        yuvimg = decoder.decode_frame_YUV(index)
        rgbimg = decoder.encode_frame_rgb888(index)
        jpegout = r'/tmp/yuv_decode_tempfile.jpg'
        rgbimg.save(jpegout)

        image.load(os.path.join(jpegout))
        image_scaled=image.scaled(screen.width()/2, screen.height()/2, QtCore.Qt.KeepAspectRatio)
        self.imagelb.setPixmap(QtGui.QPixmap.fromImage(image_scaled))
        self.setWindowTitle(f+":"+str(index))

class YuvPanel(QtGui.QWidget):
    def __init__(self, parent=None):
        super(YuvPanel, self).__init__()
        self.parent=parent
        self.initUI()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()

    def initUI(self):
        #filename, color, width, height,
        self.yuvfile    = ''
        self.path       = QtGui.QLabel()
        self.path.setText(self.yuvfile)
        self.choose     = QtGui.QPushButton('YUV File')

        self.layout_file = QtGui.QHBoxLayout()
        self.layout_file.addWidget(self.path)
        self.layout_file.addWidget(self.choose)

        self.color_tag       = QtGui.QLabel()
        self.color_tag.setText(str("format"+' '*4))
        self.color = COLOR_LIST[0]
        self.color_box =QtGui.QComboBox()
        self.color_box.setEnabled(True)
        self.color_box.addItems(COLOR_LIST)
        self.layout_color = QtGui.QHBoxLayout()
        self.layout_color.addWidget(self.color_tag)
        self.layout_color.addWidget(self.color_box)

        self.imgwidth       = 640
        self.imgheight      = 480
        self.width_lineEdit = QtGui.QLineEdit()
        self.height_lineEdit = QtGui.QLineEdit()
        self.width_lineEdit.setText(str(self.imgwidth))
        self.height_lineEdit.setText(str(self.imgheight))

        self.width_tag = QtGui.QLabel()
        self.height_tag = QtGui.QLabel()
        self.width_tag.setText(str("width"+' '*5))
        self.height_tag.setText(str("height"+' '*4))
        self.layout_width = QtGui.QHBoxLayout()
        self.layout_width.addWidget(self.width_tag)
        self.layout_width.addWidget(self.width_lineEdit)
        self.layout_height = QtGui.QHBoxLayout()
        self.layout_height.addWidget(self.height_tag)
        self.layout_height.addWidget(self.height_lineEdit)

        self.frameindex = 0
        self.frame_tag = QtGui.QLabel()
        self.frame_tag.setText(str("frameIndex"))
        self.frame_idx = QtGui.QLineEdit()
        self.frame_idx.setText(str(self.frameindex))

        self.layout_frame= QtGui.QHBoxLayout()
        self.layout_frame.addWidget(self.frame_tag)
        self.layout_frame.addWidget(self.frame_idx)

        self.ok_button = QtGui.QPushButton('OK')

        self.vlay = QtGui.QVBoxLayout()
        self.vlay.addLayout(self.layout_file)
        self.vlay.addLayout(self.layout_color)
        self.vlay.addLayout(self.layout_width)
        self.vlay.addLayout(self.layout_height)
        #self.vlay.addLayout(self.layout_frame)
        #self.vlay.addWidget(self.slider)
        self.vlay.addWidget(self.ok_button)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addLayout(self.vlay)
        self.setLayout(self.layout)

        ##link with event handler
        self.connect(self.choose, QtCore.SIGNAL('clicked()'), self.click_choosefile)
        self.connect(self.color_box, QtCore.SIGNAL('activated(const QString&)'), self.colorChange)
        self.connect(self.width_lineEdit, QtCore.SIGNAL('returnPressed()'),self.update_width)
        self.connect(self.height_lineEdit, QtCore.SIGNAL('returnPressed()'),self.update_height)
        self.connect(self.frame_idx, QtCore.SIGNAL('returnPressed()'),self.update_frameindex)
        self.connect(self.ok_button, QtCore.SIGNAL('clicked()'), self.click_ok)

        self.setWindowModality(QtCore.Qt.ApplicationModal) #should before show
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        centerWindow(self)
        #self.connect(self.slider, QtCore.SIGNAL('valueChanged(int)'), self.display)
        #self.display(0)

    def click_choosefile(self):
        filename = QtGui.QFileDialog.getOpenFileName(
                self,
                self.tr("Open YUV File"),
                QtCore.QDir.currentPath(),
                "YUV files (*.yuv);;All files(*.*)"
                )
        print "choose YUV file: %s" % str(filename)
        filename=str(filename)
        if not os.path.isfile(filename):
            QtGui.QMessageBox.about(self,'Error','Invalid file specified, %s!' % filename)
            return
        self.yuvfile = filename
        self.path.setText(self.yuvfile)

    def colorChange(self, input_qstring):
        color = str(input_qstring)
        print "color changed to: %s" % color
        self.color = color

    def update_width(self):
        width = self.width_lineEdit.text()
        width = int(width)
        self.imgwidth = width
        print "update image width: %s" % (width)

    def update_height(self):
        height = self.height_lineEdit.text()
        height = int(height)
        self.imgheight = height
        print "update image height: %s" % (height)

    def update_frameindex(self):
        frameindex = self.frame_idx.text()
        frameindex = int(frameindex)
        self.frameindex = frameindex
        print "update frame index: %s" % (frameindex)

    def click_ok(self):
        self.imgwidth = int(self.width_lineEdit.text())
        self.imgheight = int(self.height_lineEdit.text())
        print self.yuvfile, self.color, self.imgwidth, self.imgheight
        self.sliderPanel = sliderPanel(self, self.yuvfile, self.color, self.imgwidth, self.imgheight)

    def prepareVideo(self,videoname):
        print "Decode stream file %s" %videoname
        self.videoname=videoname
        cap=cv2.VideoCapture(str(videoname))
        if not cap.isOpened():
            msg="ERROR:Failed to open video %s" % videoname
            print msg
            QtGui.QMessageBox.about(None,'Error',msg)
            return False
        self.cap=cap
        self.totalFrameNumber = int(cap.get(cv.CV_CAP_PROP_FRAME_COUNT))
        print("INFO:Total frame count=%d" % self.totalFrameNumber)

        self.width = cap.get(cv.CV_CAP_PROP_FRAME_WIDTH)
        self.height = cap.get(cv.CV_CAP_PROP_FRAME_HEIGHT)
        self.fps = cap.get(cv.CV_CAP_PROP_FPS)
        self.codec = cap.get(cv.CV_CAP_PROP_FOURCC)
        self.docvt = cap.get(cv.CV_CAP_PROP_CONVERT_RGB)
        print("INFO:frame size=%dx%d, fps=%d, codec=%s, docvt=%d" %(self.width, self.height, self.fps, self.codec, self.docvt))
        return True

    def display(self, index):
        ##FIXME:here re-open stream once again as cv2 CV_CAP_PROP_POS_FRAMES operation may skip some frames,
        ##and could not handle backward seek correctly. maybe one bug.

        self.cap=cv2.VideoCapture(str(self.videoname))

        if not self.cap.isOpened():
            msg="ERROR:Failed to open video %s" % self.videoname
            print msg
            QtGui.QMessageBox.about(None,'Error',msg)
            return False

        ret, img = self.decodeFile(self.cap, index, self.docvt)
        if not ret or img is None:
            print("ERROR: Fail to get frame %d" %i)
            return
        print "display index: %s" % index

        ##for debug only
        #cv2.imshow("track", img)
        #cv2.waitKey(1)
        img=cv2.cvtColor(img, cv.CV_BGR2RGB) #convert color, otherwise, dstcvimg.copy() & QtGui.QImage.rgbSwapped() is required
        stride=img.strides[0]
        h,w=img.shape[0:2]
        data=img.data
        image = QtGui.QImage(data, w, h, stride,  QtGui.QImage.Format_RGB888) #image.rgbSwapped()

        screen = QtGui.QDesktopWidget().screenGeometry()
        image_scaled=image.scaled(screen.width()/2, screen.height()/2, QtCore.Qt.KeepAspectRatio)
        self.imagelb.setPixmap(QtGui.QPixmap.fromImage(image_scaled))
        self.setWindowTitle(os.path.basename(self.videoname) + ":"+ str(index))

    def decodeFile(self, cap, idx, docvt):
        if not cap.isOpened():
            print("ERROR:Failed to open video %s" % source)
            return False
        ret = True
        frame = None
        cap.set(cv.CV_CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            print("ERROR:fail to read frame %d" % idx)
        return ret, frame

    def mouseDoubleClickEvent(self, event):
        if event.button() != QtCore.Qt.RightButton:
            event.accept()
            return
        print "mouseDoubleClickEvent"

        index=self.slider.value()
        imgfile = ""
        print "time tag for file: %s, index: %d" % (imgfile, index)
        if len(self.pntInfo) == 2:
            self.pntInfo=[]
        self.pntInfo.append((imgfile, int(index)))

        for i in range(2):
            if i <= len(self.pntInfo)-1:
                self.showPntList[i].setText('%s:%s'%(self.pntInfo[i][0], self.pntInfo[i][1]))
            else:
                self.showPntList[i].setText('')
        if len(self.pntInfo) == 2:
            self.delta.setText('Delta Index:%d' % (self.pntInfo[1][1]-self.pntInfo[0][1]))
        else:
            self.delta.setText('Delta Index:')

        event.accept()
        return

    def click_buttonGroup(self, i):
        if i not in [0,1]:
            return
        info = self.showPntList[i].text()
        index, f = self.getClosestImgFromTimeTag(info.split(':')[1])
        self.slider.setValue(index)

class PicPanel(QtGui.QWidget):
    def __init__(self, parent, folder):
        super(PicPanel, self).__init__()
        self.parent=parent
        self.folder=folder

        fList=sorted([pic for pic in os.listdir(self.folder) if pic.split('.')[-1].lower() in ['gif', 'bmp', 'jpg', 'png']])
        if fList is None or len(fList) == 0:
            print "ERROR: No images found in %s" % folder
            QtGui.QMessageBox.about(None,'Error','No images found in %s' % folder)
            return

        fList.sort()
        self.fList=fList
        self.initUI()
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()

    def initUI(self):
        self.slider=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(self.fList)-1)
        self.layout = QtGui.QVBoxLayout()

        self.imagelb=QtGui.QLabel()
        self.imagelb.setAlignment(QtCore.Qt.AlignLeft)
        self.imagelb.setToolTip("doubleClickRightMouse to pin location")
        self.layout.addWidget(self.imagelb)
        self.layout.addWidget(self.slider)

        self.pntInfo=[]
        #manual split button
        self.showPntGroup=QtGui.QButtonGroup(self)
        self.showPntList=[]
        for i in [0,1]:
            button = QtGui.QPushButton('')
            button.setStyleSheet("background-color: rgb(218, 133, 250)");
            self.showPntList.append(button)
            self.showPntGroup.addButton(button, i)
        self.connect(self.showPntGroup, QtCore.SIGNAL('buttonClicked(int)'), self.click_buttonGroup)

        self.delta=QtGui.QLabel('Delta Index:')
        self.delta.setStyleSheet("background-color: rgb(218, 133, 250)");

        #summary_manual.txt
        #initialize the manual split rows with contents in summary_manual.txt
        outfile = os.path.join(self.folder, 'summary_manual.txt')
        if os.path.isfile(outfile):
            with open(outfile, 'r') as f:
                lines = [line.strip() for line in f.readlines()]
                print "Load manual split result from file: %s, contents: %s" % (outfile, lines)
                if len(lines) > 3:
                    print "ERROR: invalid manual split result file: %s, %s" % (outfile, lines)
                else:
                    try:
                        for i in range(len(self.showPntList)):
                            pat=lines[i]
                            self.showPntList[i].setText(pat)

                        pat=lines[2]
                        self.delta.setText(pat)
                    except Exception,e:
                        pass

        self.save=QtGui.QPushButton('Save')
        self.save.setStyleSheet("background-color: rgb(218, 133, 250)");
        self.connect(self.save, QtCore.SIGNAL('clicked()'), self.click_save)

        self.process=QtGui.QPushButton('Process')
        self.process.setStyleSheet("background-color: rgb(218, 133, 250)");

        self.vlay = QtGui.QVBoxLayout()

        self.commandhistory=QtGui.QLabel('Command List:')
        self.vlay.addWidget(self.commandhistory)

        #cmdlist.txt column
        #the cmdlist.txt file format should be:
        #   start:monthday-hour-min-sec-millisecond:eventtype
        #   stop:monthday-hour-min-sec-millisecond:eventtype
        #   ...
        cmdfile_list = [os.path.join(self.folder, 'cmdlist.txt'), os.path.join(self.folder, '..', 'cmdlist.txt')]
        cmdfile = None
        for f in cmdfile_list:
            if os.path.isfile(f):
                cmdfile = f
                print "Found cmdlist file: %s" % cmdfile
                break
        if cmdfile:
            with open(cmdfile) as f:
                lines = [line.split()[0] for line in f.readlines()]
                print "Load cmdlist from file: %s, contents: %s" % (cmdfile, lines)

            self.comboBox = QtGui.QComboBox()
            self.comboBox.addItems(lines)
            self.vlay.addWidget(self.comboBox)

            self.connect(self.comboBox, QtCore.SIGNAL('activated(const QString&)'), self.comboChange)
        else:
            print "No cmdlist file found in: %s" % cmdfile_list

        self.pinlocation=QtGui.QLabel('User Specified Location:')

        self.vlay.addWidget(self.pinlocation)
        for i in range(len(self.showPntList)):
            self.vlay.addWidget(self.showPntList[i])

        self.hlay_line = QtGui.QHBoxLayout()
        self.hlay_line.addWidget(self.delta)
        self.hlay_line.addWidget(self.save)
        self.hlay_line.addWidget(self.process)
        self.hlay_line.setStretch(0,5)
        self.hlay_line.setStretch(1,1)
        self.vlay.addLayout(self.hlay_line)

        self.layout.addLayout(self.vlay)

        self.setLayout(self.layout)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        centerWindow(self)
        self.connect(self.slider, QtCore.SIGNAL('valueChanged(int)'), self.display)
        self.display(0)

    def getClosestImgFromTimeTag(self, timetag):
        if not self.fList:
            return -1, None
        for index,f in enumerate(self.fList):
            print timetag
            if f.split('.')[0] >= timetag:
                break
        return index, f

    def comboChange(self, input_qstring):
        line = str(input_qstring)
        print "comboChange to: %s" % line
        pin_tag=line.split(':')[1]
        fsample=self.fList[0].split('.')[0]
        sep_list=['-','_']
        for sep in sep_list:
            if len(pin_tag.split(sep)) != len(fsample.split(sep)):
                print "time pattern in cmdlist file: %s is different with file name: %s" % (pin_tag, fsample)
                return
        index, f = self.getClosestImgFromTimeTag(pin_tag)

        print "Jump to nearest frame: %s, index: %s" %(f,index)
        self.slider.setValue(index)
        return

    def display(self, index):
        image = QtGui.QImage()
        imgfile = self.fList[index]
        print "display file: %s, index: %s" % (imgfile,index)

        screen = QtGui.QDesktopWidget().screenGeometry()
        image.load(os.path.join(self.folder, imgfile))
        image_scaled=image.scaled(screen.width()/2, screen.height()/2, QtCore.Qt.KeepAspectRatio)
        self.imagelb.setPixmap(QtGui.QPixmap.fromImage(image_scaled))
        self.setWindowTitle(imgfile+":"+str(index))

    def mouseDoubleClickEvent(self, event):
        if event.button() != QtCore.Qt.RightButton:
            event.accept()
            return
        print "mouseDoubleClickEvent"

        index=self.slider.value()
        imgfile = self.fList[index]
        print "time tag for file: %s, index: %d" % (imgfile, index)

        if len(self.pntInfo) == 2:
            self.pntInfo=[]
        self.pntInfo.append((imgfile, int(index)))

        for i in range(2):
            if i <= len(self.pntInfo)-1:
                imgfile,index = self.pntInfo[i][0], self.pntInfo[i][1]
                normStr=self.getNormStr(imgfile, index)
                self.showPntList[i].setText(normStr)
            else:
                self.showPntList[i].setText('')
        if len(self.pntInfo) == 2:
            self.delta.setText('Delta Index:%d' % (self.pntInfo[1][1]-self.pntInfo[0][1]))
        else:
            self.delta.setText('Delta Index:')

        event.accept()
        return

    def click_buttonGroup(self, i):
        if i not in [0,1]:
            return
        info = self.showPntList[i].text()
        index, f = self.getClosestImgFromTimeTag(info.split(':')[1])
        self.slider.setValue(index)

    def click_save(self):
        outfile = os.path.join(self.folder, 'summary_manual.txt')
        if os.path.isfile(outfile):
            os.remove(outfile)
        with open(outfile, 'a') as f:
            cnt=0
            for button in self.showPntList:
                normStr=button.text()
                if normStr != '':
                    f.write( '%s\n' % normStr)
                    cnt+=1
            if cnt == 2:
                f.write(self.delta.text()+'\n')
        print "Save manual split result to: %s" % outfile
        QtGui.QMessageBox.about(self,'Info','Manual split result saved to:\n%s.' % outfile)

    def getNormStr(self, imagefile, index):
        ret = "index-%d:%s:ManualSplit" % (index, imagefile.split('.')[0])
        return ret

    def isValidOutputDir(self, dirpath):
        contents = os.listdir(dirpath)
        fileList=['src', 'calibrate']
        for f in fileList:
            if f not in contents:
                return False
        return True

    def _updateFrameCountResult(self, dirpath):
        #post-process based on framecount solution.
        FrameCount.parseLF(dirpath)

        ##import logReport
        ##logReport.process(dirpath, 1000)

    def _updateDiffImage(self):
        QS=self.scaleline.text()
        scale = int(QS)
        image = QtGui.QImage()
        screen = QtGui.QDesktopWidget().screenGeometry()
        dirpath = os.path.split(self.folder)[0]
        imgfile = os.path.join(dirpath, 'tmpdir', 'result_phase.png')
        print "update iamge: %s with scale: %s" % (imgfile, scale)

        #do process, and update the LTF illustration image & summary report
        status = self._updateFrameCountResult(dirpath)

        image.load(imgfile)
        image_scaled=image.scaled(screen.width()/2, screen.height()/2, QtCore.Qt.KeepAspectRatio)
        self.diff_image.setPixmap(QtGui.QPixmap.fromImage(image_scaled))
        self.setWindowTitle(imgfile)

        #update summary report
        cont = self._getSummaryData(dirpath)
        self.browser.setPlainText(cont)
        self.browser.show()

    def showDiffData(self, dirpath):
        self.diff_image = QtGui.QLabel()
        self.diff_image.setToolTip("frame difference")

        self.scale_info = QtGui.QLabel('LTF detection scale (image pixels/detection pixels):')
        self.scaleline = QtGui.QLineEdit()
        self.scaleline.setValidator(QtGui.QIntValidator(self.scaleline))
        self.scaleline.setText('2000')
        self.connect(self.scaleline, QtCore.SIGNAL('returnPressed()'),self._updateDiffImage)

        self.info_layout = QtGui.QHBoxLayout()
        self.info_layout.addWidget(self.scale_info)
        self.info_layout.addWidget(self.scaleline)

        self.diff_layout = QtGui.QVBoxLayout()
        self.diff_layout.addWidget(self.diff_image)
        self.diff_layout.addLayout(self.info_layout)

        #show summary report
        self.browser = QtGui.QTextBrowser()
        self.browser.setPlainText("")
        self.diff_layout.addWidget(self.browser)

        self.diff_widget = QtGui.QWidget()
        self.diff_widget.setLayout(self.diff_layout)

        self.diff_widget.setWindowModality(QtCore.Qt.ApplicationModal)
        self.diff_widget.show()
        self._updateDiffImage()


    def _getSummaryData(self, dirpath):
        framecount_longframe = []
        framecount_fps = 0
        image_longframe = []
        image_fps = 0
        lijian_longframe = []
        lijian_fps = 0

        longframe_file=os.path.join(dirpath,"longframe.txt")

        if os.path.isfile(longframe_file):
            longframe_list = open(longframe_file).read().split(os.linesep)
            framecount_start_index = 0
            framecount_end_index = 0
            found_framecount = False
            for i in range(0, len(longframe_list)):
                if longframe_list[i].strip() == "@FRAMECOUNT":
                    found_framecount = True
                    framecount_start_index = i + 1
                elif longframe_list[i].strip() == "@END" and found_framecount:
                    framecount_end_index = i - 1
                    break
            if not abs(framecount_start_index - framecount_end_index) < 1:
                for i in range(framecount_start_index, framecount_end_index + 1):
                    framecount_longframe.append(longframe_list[i])

            framecountfps_start_index = 0
            framecountfps_end_index = 0
            found_framecountfps = False
            for i in range(0, len(longframe_list)):
                if longframe_list[i].strip() == "@FRAMECOUNT_FPS":
                    found_framecountfps = True
                    framecountfps_start_index = i + 1
                elif longframe_list[i].strip() == "@END" and found_framecountfps:
                    framecountfps_end_index = i - 1
                    break
            if not abs(framecountfps_start_index - framecountfps_end_index) < 1:
                framecount_fps = float(longframe_list[framecountfps_end_index])

            image_start_index = 0
            image_end_index = 0
            found_image = False
            for i in range(0, len(longframe_list)):
                if longframe_list[i].strip() == "@IMAGE":
                    found_image = True
                    image_start_index = i + 1
                elif longframe_list[i].strip() == "@END" and found_image:
                    image_end_index = i - 1
                    break
            if not abs(image_start_index - image_end_index) < 1:
                for i in range(image_start_index, image_end_index + 1):
                    image_longframe.append(longframe_list[i])
        
            imagefps_start_index = 0
            imagefps_end_index = 0
            found_imagefps = False
            for i in range(0, len(longframe_list)):
                if longframe_list[i].strip() == "@IMAGE_FPS":
                    found_imagefps = True
                    imagefps_start_index = i + 1
                elif longframe_list[i].strip() == "@END" and found_imagefps:
                    imagefps_end_index = i - 1
                    break
            if not abs(imagefps_start_index - imagefps_end_index) < 1:
                image_fps = float(longframe_list[imagefps_end_index])
        
        lijian_fps_file = os.path.join(dirpath, "lijian_fps.txt")
        if os.path.isfile(lijian_fps_file): 
            lijian_fps = float(open(lijian_fps_file).read().split("=")[1].strip())
        lijian_longframe_file = os.path.join(dirpath, "lijian_longframe.txt")
        if os.path.isfile(lijian_longframe_file):
            lijian_longframe = open(lijian_longframe_file).read().split(os.linesep)

        ret =  "FrameCount FPS: " + str(framecount_fps) + os.linesep \
             + "FrameCount LongFrame: " + os.linesep \
             + os.linesep.join(framecount_longframe) + os.linesep \
             + "===========================================" + os.linesep \
             + "Image FPS: " + str(image_fps) + os.linesep \
             + "Image LongFrame: " + os.linesep \
             + os.linesep.join(image_longframe) + os.linesep \
             + "===========================================" + os.linesep \
             + "LiJian FPS: " + str(lijian_fps) + os.linesep \
             + "LiJian LongFrame: " + os.linesep \
             + os.linesep.join(lijian_longframe) + os.linesep
        return ret

    def click_result(self, dirpath=None):
        if (not dirpath) or (not os.path.isdir(dirpath)): #canceled
            return
        if not self.isValidOutputDir(dirpath):
            QtGui.QMessageBox.about(self,'Error','Invalid folder specified!')
            return
        print "show folder: %s" % dirpath
        ##---------------------------------------------------------

        #display frame_diff images and adjustable threshold
        self.showDiffData(dirpath)

class DataInspector(QtGui.QWidget):
    def __init__(self, parent = None):
        super(DataInspector, self).__init__()
        self.initUI()

    def initUI(self):
        self.picButton=QtGui.QPushButton('PicViewer')
        self.videoButton=QtGui.QPushButton('YUVViewer')

        self.connect(self.picButton, QtCore.SIGNAL('clicked()'), self.click_viewPic)
        self.connect(self.videoButton, QtCore.SIGNAL('clicked()'), self.click_viewVideo)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.picButton)
        layout.addWidget(self.videoButton)
        self.setLayout(layout)

        self.setWindowTitle('DataInspector')
        self.setWindowModality(QtCore.Qt.ApplicationModal) #should before show
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        centerWindow(self)

    def click_viewPic(self):
        #specify the folder contain images to display
        dirpath = str(QtGui.QFileDialog.getExistingDirectory(
            self,
            self.tr("Open Directory"),
            QtCore.QDir.currentPath(),
            QtGui.QFileDialog.ShowDirsOnly | QtGui.QFileDialog.DontResolveSymlinks)
            )
        if os.path.isdir(dirpath):
            print "viewPic from folder: %s" % dirpath
            self.picPan = PicPanel(self, dirpath)

    def click_viewVideo(self):
        self.yuvPan = YuvPanel(self)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    #inspect=DataInspector()
    inspect=YuvPanel()
    inspect.show()
    sys.exit(app.exec_())

