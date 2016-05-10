#!/usr/bin/env python3

# Convert a BMP source file to Python source.

# Copyright Robert Hammelrath and Peter Hinch 2016
# Released under the MIT licence
# Files created by any graphic tool exporting bmp files, e.g. gimp
# the colour depth may be 1, 4, 8, 16, or 24 pixels, lower sizes preferred

# Usage:
# ./bmp_to_icon checkbox_on.bmp checkbox_off.bmp
# puts files into a single Python file defaulting to icons.py (-o name can override default)
# with a dictionary 'icons' indexed by a number.
# The generated icon pathon script also defines a function get_icon(index) 
# for accessing an icon, which returns a tuple which can directly supplied 
# into the drawBitmap() function of the tft lib.
# -------------------------
# Example: Assuming an icons file called icons.py.
# then the sript usign it could look like:
#
# import tft
# import icons
# .....
# mytft = tft.TFT()
# .....
# mytft.drawBitmap(x1, y1, *icons.get_icon(0))  # draw the first icon at location x1, y1
# mytft.drawBitmap(x2, y2, *icons.get_icon(1))  # draw the scond icon at location x2, y2


import os
import argparse
from struct import unpack

# define symbol shared with repetive call as global
icon_width = None
icon_height = None
icon_colortable = None
icon_colors = None
icon_table = []
no_icons = 0

# split read, due to the bug in the SD card library, avoid reading
# more than 512 bytes at once, at a performance penalty
# required if the actual file position is not a multiple of 4
def split_read(f, buf, n):
    BLOCKSIZE = 512 ## a sector
    mv = memoryview(buf)
    bytes_read = 0
    for i in range(0, n - BLOCKSIZE, BLOCKSIZE):
        bytes_read += f.readinto(mv[i:i + BLOCKSIZE])
    if bytes_read < n and (n - bytes_read) <= BLOCKSIZE:
        bytes_read += f.readinto(mv[bytes_read:n])
    return bytes_read


def getname(sourcefile):
    return os.path.basename(os.path.splitext(sourcefile)[0])

# pack into bit from buf into res in bits sized chunks
def explode(buf, res, offset, size, bits):
    bm_ptr = 0
    shift = 8 - bits
    outmask = ((1 << bits) - 1)
    bitmask = outmask << shift
    for j in range(size):
        res[offset] = ((buf[bm_ptr] & bitmask) >> shift) & outmask
        bitmask >>= bits
        shift -= bits
        offset += 1
        if bitmask == 0: # mask rebuild & data ptr advance on byte exhaust
            shift = 8 - bits
            bitmask = outmask << shift
            bm_ptr += 1
    return offset

def implode(buf, size, colors):
    op = 0
    ip = 0
    if colors == 1: # pack 8 in one
        for ip in range(0, size, 8):
            buf[op] = (buf[ip] << 7 |
                       buf[ip + 1] << 6 |
                       buf[ip + 2] << 5 |
                       buf[ip + 3] << 4 |
                       buf[ip + 4] << 3 |
                       buf[ip + 5] << 2 |
                       buf[ip + 6] << 1 |
                       buf[ip + 7])
            op += 1
    elif colors == 2: # pack 4 in 1
        for ip in range(0, size, 4):
            buf[op] = (buf[ip] << 6 |
                       buf[ip + 1] << 4 |
                       buf[ip + 2] << 2 |
                       buf[ip + 3])
            op += 1
    elif colors == 4: # pack 2 in 1
        for ip in range(0, size, 2):
            buf[op] = (buf[ip] << 4 |
                       buf[ip + 1])
            op += 1
    else : # just copy
        for ip in range(size):
            buf[op] = buf[ip]
            op += 1
    return op

def process(f, outfile):
# 
    global icon_width
    global icon_height
    global icon_colortable
    global icon_colors
    global icon_table
    global no_icons
    
    BM, filesize, res0, offset = unpack("<hiii", f.read(14))
    (hdrsize, imgwidth, imgheight, planes, colors, compress, imgsize, 
     h_res, v_res, ct_size, cti_size) = unpack("<iiihhiiiiii", f.read(40))
# test consistency in a set
# 
    if icon_width is not None and icon_width != imgwidth:
        print ("Error: All icons in a set must have the same width")
        return None
    else:
        icon_width = imgwidth
    if icon_height is not None and icon_height != imgheight:
        print ("Error: All icons in a set must have the same heigth")
        return None
    else:
        icon_height = imgheight
        
    if icon_colors is not None and icon_colors != colors:
        print ("Error: All icons in a set must have the same number of colors")
        return None
    else:
        icon_colors = colors
        
    if colors in (1,4,8):  # must have a color table
        if ct_size == 0: # if 0, size is 2**colors
            ct_size = 1 << colors
        colortable = bytearray(ct_size * 4)
        f.seek(hdrsize + 14) # go to colortable
        n = split_read(f, colortable, ct_size * 4) # read colortable
        if icon_colortable is None:
            icon_colortable = colortable
        if colors == 1:
            bsize = (imgwidth + 7) // 8
            res = bytearray((imgwidth * imgheight * 8) + 8) # make it big enough
        elif colors == 4:
            bsize = (imgwidth + 1) // 2
            res = bytearray((imgwidth * imgheight * 2) + 2) # make it big enough
        elif colors == 8:
            bsize = imgwidth
            res = bytearray((imgwidth * imgheight) + 1) # make it big enough
        rsize = (bsize + 3) & 0xfffc # read size must read a multiple of 4 bytes
        f.seek(offset)
        icondata = []
        for row in range(imgheight):
            b = bytearray(rsize)
            n = split_read(f, b, rsize)
            if n != rsize:
                print ("Error reading file")
                return None
            icondata.append(b) # read all lines
# convert data            
        offset = 0
        for row in range(imgheight - 1, -1, -1):
            offset = explode(icondata[row], res, offset, imgwidth, colors)
        if colors == 4 and ct_size <= 4: # reduce color size from 4 to 2 is feasible
            colors = 2
            icon_colors = colors
        offset = implode(res, offset, colors)
# store data
        outfile.write("{}: (\n".format(no_icons))
        for i in range(offset):
            if (i % 16) == 0:
                outfile.write("    b'")
            outfile.write("\\x{:02x}".format(res[i]))
            if (i % 16) == 15:
                outfile.write("'\n")
        if (i % 16) != 15:
            outfile.write("'\n")
        outfile.write("),\n")
    else:
        if icon_colortable is None:
            icon_colortable = bytearray(0)
        f.seek(offset)
        if colors == 16:
            bsize = imgwidth * 2
            rsize = (imgwidth*2 + 3) & 0xfffc # must read a multiple of 4 bytes
            icondata = []
            for row in range(imgheight):
                b = bytearray(rsize)
                n = split_read(f, b, rsize)
                if n != rsize:
                    print ("Error reading file")
                    return None
                icondata.append(b) # read all lines
# store data
        elif colors == 24:
            bsize = imgwidth * 3
            rsize = (imgwidth*3 + 3) & 0xfffc # must read a multiple of 4 bytes
            icondata = []
            for row in range(imgheight):
                b = bytearray(rsize)
                n = split_read(f, b, rsize)
                if n != rsize:
                    print ("Error reading file")
                    return None
                icondata.append(b) # read all lines
#                
        outfile.write("{}: (\n".format(no_icons))
        for row in range(imgheight - 1, -1, -1):
            for i in range (bsize):
                if (i % 16) == 0:
                    outfile.write("    b'")
                outfile.write("\\x{:02x}".format(icondata[row][i]))
                if (i % 16) == 15:
                    outfile.write("'\n")
            if (i % 16) != 15:
                outfile.write("'\n")
        outfile.write("),\n")
    no_icons += 1
    return no_icons

def write_header(outfile):
    outfile.write("""
# Code generated by bmp_to_icon.py
from uctypes import addressof

"""
)
    outfile.write("_icons = { \n")
  
def write_trailer(outfile):
    outfile.write('}\n\n')
    outfile.write("colortable = { 0: (\n    b'")
    size = len(icon_colortable)
    if (size >= 8): # only for bitmaps with a colortable
        icon_colortable[3] = icon_colors  # store color bits in table
    for i in range(size):
        outfile.write("\\x{:02x}".format(icon_colortable[i]))
        if (i % 16) == 15 and i != (size - 1):
            outfile.write("'\n    b'")
    outfile.write("')\n}\n")
    outfile.write("width = {}\n".format(icon_width))
    outfile.write("height = {}\n".format(icon_height))
    outfile.write("colors = {}\n".format(icon_colors))
    outfile.write("""
def get_icon(icon_index = 0, color_index = 0):
    return width, height, addressof(_icons[icon_index]), colors, addressof(colortable[color_index])
    
def draw(x, y, icon_index, draw_fct, color_index = 0):
    draw_fct(x - width//2, y - height // 2, width, height, addressof(_icons[icon_index]), colors, addressof(colortable[color_index]))
""")

def load_bmp(sourcefiles, destfile):
    try:
        with open(getname(destfile) + ".py", 'w') as outfile:
            write_header(outfile)
            for sourcefile in sourcefiles:
                with open(sourcefile, 'rb') as f:
                    if process(f,  outfile) is None:
                        break
            write_trailer(outfile)
    except OSError as err:
        print(err)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__file__, description = 
"""Utility for producing a icon set file for the tft module by converting BMP files. 
Sample usage: ./bmp_to_icon.py checkbox_empty.bmp checkbox_tick.bmp
Produces icons.py""",
    formatter_class = argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infiles', metavar ='N', type = str, nargs = '+', help = 'input file paths')
    parser.add_argument("--outfile", "-o", default = 'icons', help = "Path and name of output file (w/o extension)", required = False)
    args = parser.parse_args()
    errlist = [f for f in args.infiles if not f[0].isalpha()]
    if len(errlist):
        print('Font filenames must be valid Python variable names:')
        for f in errlist:
            print(f)
    if len(errlist) == 0:
        errlist = [f for f in args.infiles if not os.path.isfile(f)]
        if len(errlist):
            print("These bmp filenames don't exist:")
            for f in errlist:
                print(f)
    if len(errlist) == 0:
        errlist = [f for f in args.infiles if os.path.splitext(f)[1].lower() != '.bmp']
        if len(errlist):
            print("These filenames don't appear to be bmp files:")
            for f in errlist:
                print(f)
    if len(errlist) == 0:
        load_bmp(args.infiles, args.outfile)


