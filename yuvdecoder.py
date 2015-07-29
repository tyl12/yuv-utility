#!/usr/bin/python


from numpy import *
import getopt
import os
import sys
import Image
import time
screenLevels = 255.0

def round_val(val):
    val=int(val)
    if val <= 255 and val >= 0 :
        return val
    if val<0:
        return 0
    if val>255:
        return 255

class YUVDecoder:

    __DECODE_MAP = {
            #color:[bit per pixel, desc]
            'I420':[12, "8 bit Y plane followed by 8 bit 2x2 subsampled U and V planes."],
            'YV12':[12, "8 bit Y plane followed by 8 bit 2x2 subsampled V and U planes."],
            'NV12':[12, "8-bit Y plane followed by an interleaved U/V plane with 2x2 subsampling"],
            'NV21':[12, "As NV12 with U and V reversed in the interleaved plane"],
            #'YV16':[12, "8 bit Y plane followed by 8 bit 2x1 subsampled V and U planes."],
            'UYVY':[16, "YUV 4:2:2 (Y sample at every pixel, U and V sampled at every second pixel \
                    horizontally on each line). A macropixel contains 2 pixels in 1 u_int32."],
            'YUYV':[16, "Duplicate of YUY2. YUV 4:2:2 as for UYVY but with different component \
                    ordering within the u_int32 macropixel."],
            'YVYU':[16, "YUV 4:2:2 as for UYVY but with different component ordering within the \
                    u_int32 macropixel."],
            }

    @classmethod
    def get_color_list(cls):
        color_list = cls.__DECODE_MAP.keys()
        return color_list

    @classmethod
    def getbpp(cls, color):
        return cls.__DECODE_MAP[color][0]

    def __init__(self, filename, color, row, col):
        self.__file = filename
        self.__color = color
        self.__row = row
        self.__col = col
        #self.__inplace = True # in-place yuv->rgb conversion
        self.__inplace = False # in-place yuv->rgb conversion
        if not os.path.isfile(filename):
            raise Exception("ERROR: invalid file %s" % filename)
        self.__fd = open(filename, 'rb')
        self.__func = None
        if color == 'I420':
            self.__func = self.decode_i420
        elif color == 'NV21':
            self.__func = self.decode_nv21
        elif color == 'NV12':
            self.__func = self.decode_nv12
        elif color == 'YV12':
            self.__func = self.decode_yv12
        elif color == 'UYVY':
            self.__func = self.decode_uyvy
        elif color == 'YUYV':
            self.__func = self.decode_yuyv
        elif color == 'YVYU':
            self.__func = self.decode_yvyu

        if not self.__func:
            raise Exception("ERROR: no available decode func for color format %s" % color)


    def decode_frame_YUV(self, frame_idx):
        print "decode frame index: %s" % frame_idx
        t_start = time.time()
        self.__yuvimg = self.__func(frame_idx)
        t_stop = time.time()
        print "Info: time cost for decode:", t_stop-t_start
        return self.__yuvimg

    def decode_i420(self, frame_idx):
        fp = self.__fd
        ROW = self.__row
        COL = self.__col
        bpp=self.getbpp('I420')
        blk_size = ROW*COL * 12 / 8  #bytes
        fp.seek(blk_size*frame_idx,0)

        yuvimg=Image.new('RGB',(COL, ROW),(0, 0, 0))
        pixel=yuvimg.load()

        raw_buf=[]
        rem=blk_size
        while rem != 0:
            s=fp.read(rem);
            if s == '': #handle EOF
                break
            raw_buf += s
            rem -= len(s)

        for i in range(blk_size):
            raw_buf[i]=ord(raw_buf[i])

        y_baseoffset = 0
        u_baseoffset = y_baseoffset + ROW*COL
        v_baseoffset = u_baseoffset + ROW*COL/4
        for m in range(ROW):
            for n in range(COL):
                y_idx = y_baseoffset + m*COL + n
                y = raw_buf[y_idx]
                '''
                #wrong
                if m%2 == 0:
                    if n%2 == 0:
                        u_idx = u_baseoffset + int(m/2)*COL/2+ int(n/2)
                        u=raw_buf[u_idx]
                        v_idx = v_baseoffset + int(m/2)*COL/2+ int(n/2)
                        v=raw_buf[v_idx]
                u=u
                v=v
                '''
                byte_offset = int(m/2)*COL/2+ int(n/2)
                u_idx = u_baseoffset + byte_offset
                u=raw_buf[u_idx]
                v_idx = v_baseoffset + byte_offset
                v=raw_buf[v_idx]

                pixel[n,m] = (y, u, v)
        return yuvimg

    def decode_yv12(self, frame_idx):
        yuvimg = self.decode_i420(frame_idx)
        ROW = self.__row
        COL = self.__col
        pixel = yuvimg.load()
        for m in range(ROW):
            for n in range(COL):
                (y, v, u) = pixel[n,m]
                pixel[n, m] = (y, u, v)
        return yuvimg

    def decode_nv12(self, frame_idx):
        fp = self.__fd
        ROW = self.__row
        COL = self.__col
        bpp=self.getbpp('NV21')
        blk_size = ROW*COL * bpp/8  #bytes
        fp.seek(blk_size*frame_idx,0)

        yuvimg=Image.new('RGB',(COL, ROW),(0, 0, 0))
        pixel=yuvimg.load()

        raw_buf=[]
        rem=blk_size
        while rem != 0:
            s=fp.read(rem);
            raw_buf += s
            rem -= len(s)

        for i in range(blk_size):
            raw_buf[i]=ord(raw_buf[i])

        y_baseoffset = 0
        u_baseoffset = y_baseoffset + ROW*COL
        v_baseoffset = u_baseoffset + 1
        for m in range(ROW):
            for n in range(COL):
                y_idx = y_baseoffset + m*COL + n
                y = raw_buf[y_idx]
                '''
                #wrong
                if m%2 == 0:
                    if n%2 == 0:
                        #u_idx = u_baseoffset + int(m/2)*int(COL/2)+ int(n/2)*2
                        u_idx = u_baseoffset + int(m/2)*int(COL)+ int(n/2)*2
                        u=raw_buf[u_idx]
                        #v_idx = v_baseoffset + int(m/2)*int(COL/2)+ int(n/2)
                        v_idx = u_idx+1
                        v=raw_buf[v_idx]
                u=u
                v=v
                '''
                u_idx = u_baseoffset + int(m/2)*int(COL)+ int(n/2)*2
                u=raw_buf[u_idx]
                v_idx = u_idx+1
                v=raw_buf[v_idx]

                pixel[n,m] = (y, u, v)
        return yuvimg

    def decode_nv21(self, frame_idx):
        yuvimg = self.decode_nv12(frame_idx)
        ROW = self.__row
        COL = self.__col
        pixel = yuvimg.load()
        for m in range(ROW):
            for n in range(COL):
                (y, v, u) = pixel[n,m]
                pixel[n, m] = (y, u, v)
        return yuvimg

    def decode_uyvy(self, frame_idx):
        fp = self.__fd
        ROW = self.__row
        COL = self.__col
        bpp=self.getbpp('UYVY')
        blk_size = ROW*COL * bpp/8  #bytes
        fp.seek(blk_size*frame_idx,0)

        yuvimg=Image.new('RGB',(COL, ROW),(0, 0, 0))
        pixel=yuvimg.load()

        raw_buf=[]
        rem=blk_size
        while rem != 0:
            s=fp.read(rem);
            raw_buf += s
            rem -= len(s)

        for i in range(blk_size):
            raw_buf[i]=ord(raw_buf[i])

        u_baseoffset = 0
        y_baseoffset = u_baseoffset + 1
        v_baseoffset = y_baseoffset + 1
        row_step = COL*bpp/8 #bytes per row
        for m in range(ROW):
            for n in range(COL):
                y_idx = y_baseoffset + m*row_step + n*2
                y = raw_buf[y_idx]
                if n%2 == 0:
                    u_idx = u_baseoffset + m*row_step + int(n/2)*4
                    u = raw_buf[u_idx]
                    v_idx = v_baseoffset + m*row_step + int(n/2)*4
                    v = raw_buf[v_idx]
                u=u
                v=v
                pixel[n,m] = (y, u, v)
        return yuvimg

    def decode_yuyv(self, frame_idx):
        fp = self.__fd
        ROW = self.__row
        COL = self.__col
        bpp=self.getbpp('YUYV')
        blk_size = ROW*COL * bpp/8  #bytes
        fp.seek(blk_size*frame_idx,0)

        yuvimg=Image.new('RGB',(COL, ROW),(0, 0, 0))
        pixel=yuvimg.load()

        raw_buf=[]
        rem=blk_size
        while rem != 0:
            s=fp.read(rem);
            raw_buf += s
            rem -= len(s)

        for i in range(blk_size):
            raw_buf[i]=ord(raw_buf[i])

        y_baseoffset = 0
        u_baseoffset = y_baseoffset + 1
        v_baseoffset = u_baseoffset + 2
        row_step = COL*bpp/8 #bytes per row
        for m in range(ROW):
            for n in range(COL):
                y_idx = y_baseoffset + m*row_step + n*2
                y = raw_buf[y_idx]
                if n%2 == 0:
                    u_idx = u_baseoffset + m*row_step + int(n/2)*4
                    u = raw_buf[u_idx]
                    v_idx = v_baseoffset + m*row_step + int(n/2)*4
                    v = raw_buf[v_idx]
                u=u
                v=v
                pixel[n,m] = (y, u, v)
        return yuvimg

    def decode_yvyu(self, frame_idx):
        yuvimg = self.decode_yuyv(frame_idx)
        ROW = self.__row
        COL = self.__col
        pixel = yuvimg.load()
        for m in range(ROW):
            for n in range(COL):
                (y, v, u) = pixel[n,m]
                pixel[n, m] = (y, u, v)
        return yuvimg

    ###################################################################################
    def encode_frame_rgb888(self, frame_idx):
        t_start = time.time()
        ROW=self.__row
        COL=self.__col
        yuvimg=self.__yuvimg
        yuvpixel=yuvimg.load()
        if self.__inplace:
            print "Notes: inplace yuv->rgb conversion, yuv image invalidated"
            img=yuvimg
            pixel = yuvpixel
        else:
            img=Image.new('RGB',(COL, ROW),(0, 0, 0))
            pixel=img.load()

        for i in range(ROW):
            for j in range(COL):
                (y,u,v) = yuvpixel[j,i]

                '''
                choice 1
                '''
                c = y - 16
                d = u - 128
                e = v - 128

                r = ( 298 * c           + 409 * e + 128)>>8
                g = ( 298 * c - 100 * d - 208 * e + 128)>>8
                b = ( 298 * c + 516 * d           + 128)>>8

                r = round_val(r)
                g = round_val(g)
                b = round_val(b)

                '''
                choice 2
                '''
                '''or use below algorithm, but fix point one will be much faster
                r=int(y+1.4075*(v-128))
                g=int(y-0.3455*(u-128)-0.7169*(v-128))
                b=int(y+1.779*(u-128))
                '''

                '''
                choice 3
                '''
                '''
                r = 1.164 * (y-16) + 1.596 * (v - 128)
                g = 1.164 * (y-16) - 0.813 * (v - 128) - 0.391 * (u - 128)
                b = 1.164 * (y-16) + 2.018 * (u - 128)
                '''

                #img.putpixel((j,i),(r,g,b))
                pixel[j,i] = (r,g,b)

        t_stop = time.time()
        print "Info: time cost for encode:", t_stop-t_start
        return img

###################################################################################



def convert_yuv_to_jpeg(f, color, ROW, COL, dstfile):
    decoder = YUVDecoder(f, color, ROW, COL)
    for frameidx in range(1):
        yuvimg = decoder.decode_frame_YUV(frameidx)
        rgbimg = decoder.encode_frame_rgb888(frameidx)
        if not rgbimg:
            #print "ERROR: fail to parse frameidx %s" % frameidx
            print "ERROR: fail to process file %s" % f
        else:
            #rgbimg.save(r'/home/mysamba/public/rgb888_%s.jpg'%(frameidx))
            rgbimg.save(dstfile)

    return

def show_help():
    print "python yuvdecoder.py -f image -w width -h height -c color -d"
    print "supported color list:"
    color_list = YUVDecoder.get_color_list();
    for i in color_list:
        print " "*5 + i


if __name__ == '__main__':

    opts, args = getopt.getopt(sys.argv[1:], "f:w:h:c:d")
    COL = 640
    ROW = 480
    color = "NV12"
    src = "./image.yuv"
    debug_mode = False

    for op, value in opts:
        if op == "-f":
            src = str(value)
        elif op == "-w":
            COL = int(value)
        elif op == "-h":
            ROW = int(value)
        elif op == "-c":
            color = str(value)
        elif op == "-d":
            debug_mode=True

    if not os.path.exists(src):
        print "ERROR: Inavlid src: " + src
        show_help()
        exit(0)

    print "--> file: " + src
    print "--> width: " + str(COL)
    print "--> height: " + str(ROW)
    print "--> color: " + color
    print "--> debug: " + str(debug_mode)
    print "\n"


    cur_dir=os.path.abspath('.')
    basename=os.path.basename(src).split('.')[0]
    dstfile=os.path.join(cur_dir, basename+'.jpg')
    #print cur_dir
    #print basename
    #print dstfile

    convert_yuv_to_jpeg(src, color, ROW, COL, dstfile)
    print "Output: " + dstfile


