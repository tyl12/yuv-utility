yuv-utility
===========
PIL/PyQt4 based YUV viewer. Currently support FOURCC
    NV12
    NV12
    YV12
    I420
    UYVY
    YUYV
    YVYU

S/W lib requirement:
    python 2.7
    PyQt4
    PIL
    numpy

Usage:
    launch YUVUtil.py or from command line.

Known issue:
    for simplicity, YUV bytes are converted to RGB888 without any optimization.
It only work as a utility for camera/video development or debuging.


