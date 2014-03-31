#!/usr/bin/python
import sys
import os
import re
import shutil
import subprocess
import datetime
import traceback

import numpy as np
import yuvdecoder

from PyQt4 import QtGui
from PyQt4 import QtCore

import ConfigParser

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
        self.user_play_flag = False
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
        if self.user_play_flag == True:
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
            self.user_play_flag = True
            self.timer.start(gControlDurationMs, self)
        else:
            self.play.setText("Play")
            self.user_play_flag = False
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

    def read_config(self):
        if not os.path.isfile(self.config_file):
            self.imgwidth=640
            self.imgheight=480
            self.color='I420'
            self.yuvfile=''
        else:
            print "read config file"
            config = ConfigParser.ConfigParser()
            config.read(self.config_file)
            self.imgwidth=int(config.get('main','width'))
            self.imgheight=int(config.get('main','height'))
            self.color=config.get('main','color')
            self.yuvfile=config.get('main','filepath')

    def write_config(self):
        config = ConfigParser.ConfigParser()
        config.add_section("main")
        config.set('main', 'width', self.imgwidth)
        config.set('main', 'height', self.imgheight)
        config.set('main', 'color', self.color)
        config.set('main', 'filepath', self.yuvfile)
        config.write(open(self.config_file,'w+'))

    def initUI(self):
        ##update local default setting if previous config file found
        #filename, color, width, height,
        self.config_file = r'/tmp/yuvutil.conf'
        self.read_config()

        self.path       = QtGui.QLabel()
        self.path.setText(self.yuvfile)
        self.choose     = QtGui.QPushButton('YUV File')

        self.layout_file = QtGui.QHBoxLayout()
        self.layout_file.addWidget(self.path)
        self.layout_file.addWidget(self.choose)

        self.color_tag       = QtGui.QLabel()
        self.color_tag.setText(str("format"+' '*4))
        self.color_box =QtGui.QComboBox()
        self.color_box.setEnabled(True)
        self.color_box.addItems(COLOR_LIST)
        idx = self.color_box.findText(self.color)
        if idx != -1:
            self.color_box.setCurrentIndex(idx)

        self.layout_color = QtGui.QHBoxLayout()
        self.layout_color.addWidget(self.color_tag)
        self.layout_color.addWidget(self.color_box)

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
        ## save the current setting.
        self.write_config()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    inspect=YuvPanel()
    inspect.show()
    sys.exit(app.exec_())

