from numpy import *
import os
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

    def __init__(self, filename, color, row, col):
        self.__file = filename
        self.__color = color
        self.__row = row
        self.__col = col
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

        if not self.__func:
            raise Exception("ERROR: no available decode func for color format %s" % color)


    def decode_frame_YUV(self, frame_idx):
        t_start = time.time()
        self.__yuvimg = self.__func(frame_idx)
        t_stop = time.time()
        print "Info: time cost for decode:", t_stop-t_start
        return self.__yuvimg
        
    def decode_i420(self, frame_idx):
        fp = self.__fd
        ROW = self.__row
        COL = self.__col
        bpp=12
        blk_size = ROW*COL * 3 * bpp/8  #bytes
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
        v_baseoffset = u_baseoffset + ROW*COL/4
        for m in range(ROW):
            for n in range(COL):
                y_idx = y_baseoffset + m*COL + n
                y = raw_buf[y_idx]
                if m%2 == 0:
                    if n%2 == 0:
                        u_idx = u_baseoffset + int(m/2)*COL/2+ int(n/2)
                        u=raw_buf[u_idx]
                        v_idx = v_baseoffset + int(m/2)*COL/2+ int(n/2)
                        v=raw_buf[v_idx]
                u=u
                v=v
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
        bpp=12
        blk_size = ROW*COL * 3 * bpp/8  #bytes
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
                if m%2 == 0:
                    if n%2 == 0:
                        u_idx = u_baseoffset + int(m/2)*COL/2+ int(n/2)*2
                        u=raw_buf[u_idx]
                        v_idx = v_baseoffset + int(m/2)*COL/2+ int(n/2)
                        v=raw_buf[v_idx]
                u=u
                v=v
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

    def decode_yv16(self, frame_idx):
        return
    def decode_uyvy(self, frame_idx):
        return

    def encode_frame_rgb888(self, frame_idx):
        t_start = time.time()
        ROW=self.__row
        COL=self.__col
        yuvimg=self.__yuvimg
        yuvpixel=yuvimg.load()
        
        img=Image.new('RGB',(COL, ROW),(0, 0, 0))
        pixel=img.load()
        d1=d2=0
        for i in range(ROW):
            for j in range(COL):
                (y,u,v) = yuvpixel[j,i]

                c = y - 16
                d = u - 128
                e = v - 128
                
                r = ( 298 * c           + 409 * e + 128)>>8
                g = ( 298 * c - 100 * d - 208 * e + 128)>>8
                b = ( 298 * c + 516 * d           + 128)>>8
                
                '''or use below algorithm, but fix point one will be much faster
                r=int(y+1.4075*(v-128))
                g=int(y-0.3455*(u-128)-0.7169*(v-128))
                b=int(y+1.779*(u-128))
                '''
                
                r = round_val(r)
                g = round_val(g)
                b = round_val(b)

                #img.putpixel((j,i),(r,g,b))
                pixel[j,i] = (r,g,b)

        t_stop = time.time()
        print "Info: time cost for encode:", t_stop-t_start
        return img  

if __name__ == '__main__':
    ROW=288
    COL=352
    f=r'C:\Users\yiliangt\Downloads\bus_cif\bus_cif.yuv'
    color = 'I420'

    ROW=720
    COL=1280
    f=r'C:\Users\yiliangt\Downloads\bus_cif\in_to_tree_420_720p50.y4m'
    color = 'NV21'
    
    decoder = YUVDecoder(f, color, ROW, COL)
    for frameidx in range(3):
        dstfile = r'C:\Users\yiliangt\Downloads\bus_cif\bus_cif_%s.jpg' % frameidx
        yuvimg = decoder.decode_frame_YUV(frameidx)
        rgbimg = decoder.encode_frame_rgb888(frameidx)
        if not rgbimg:
            print "ERROR: fail to parse frameidx %s" % frameidx
        else:
            rgbimg.save(r'C:\Users\yiliangt\Downloads\bus_cif\rgb888_%s.jpg'%(frameidx))





    
