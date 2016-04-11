#
# Some sample code
#
import os, gc
from uctypes import addressof
from struct import unpack

from tft import *
from dejavu14 import dejavu14
from font6mono import font6mono
from font8mono import font8mono
from sevensegnumfont import sevensegnumfont
from font7hex import font7hex


sizetable = {
    "F" : 480,
    "L" : 360,
    "Q" : 272,
    "P" : 204,
    "D" : 408,
    "R" : 180
    }

def odd_read(f, n):
    BLOCKSIZE = const(512) ## a sector, but may be 4 too
    part = BLOCKSIZE - (f.tell() % BLOCKSIZE)
    if part >= n or part == BLOCKSIZE:
        return f.read(n)
    else:
        return f.read(part) + f.read(n - part)


def displayfile(mytft, name, width, height):
    with open(name, "rb") as f:
        gc.collect()
        row = 0
        color = mytft.getColor()
        mytft.setColor((0, 0, 0))
        parts = name.split(".") # get extension
        if len(parts) > 1:
            mode = parts[-1].lower()
        if mode == "raw": # raw 16 bit 565 format with swapped bytes
            imgwidth = sizetable[name[0]]
            b = bytearray(imgwidth * 2)
            for row in range(height):
                n = f.readinto(b)
                if not n:
                    break
                margin = (width - imgwidth) // 2
                if margin: ## picure with less than frame
                    mytft.drawHLine(0, row, margin)
                    mytft.drawHLine(imgwidth + margin, row, margin)
                mytft.drawBitmap(margin, row, imgwidth, 1, b, 1)
            mytft.fillRectangle(0, row, width - 1, height - 1)
        elif mode == "bmp":  # Windows bmp file
            BM, filesize, res0, offset = unpack("<hiii", f.read(14))
            hdrsize, imgwidth, imgheight, planes, colors = unpack("<iiihh", f.read(16))
#            print (name, offset, imgwidth, imgheight)
            if colors in (16, 24) and imgwidth <= width and (imgwidth % 4) == 0: ## only 16 or 24 bit colors supported
                bytes_per_pix = colors // 8
                f.seek(offset)
                hstep = imgwidth // bytes_per_pix
                skip = ((height - imgheight) // 2)
                if skip > 0:
                    mytft.fillRectangle(0, height - skip, width - 1, height - 1)
                else:
                    skip = 0
                if colors == 16:
                    b1 = bytearray(imgwidth)
                    b2 = bytearray(imgwidth)
                    for row in range(height - skip - 1, -1, -1):
# read in chunks, due to the bug in the SD card libraray, avoid reading
# more than 511 bytes at once, at a performance penalty
# required if the seek offset was not a multiple of 4
                        n1 = f.readinto(b1)
                        n2 = f.readinto(b2)
                        if not n2:
                            break
                        mytft.swapbytes(b1, n1)
                        mytft.swapbytes(b2, n2)
                        mytft.setXY(0, row, imgwidth - 1, row)
                        mytft.displaySCR565_AS(b1, hstep)
                        mytft.displaySCR565_AS(b2, hstep)
                else:
                    b1 = bytearray(imgwidth)
                    b2 = bytearray(imgwidth)
                    b3 = bytearray(imgwidth)
                    for row in range(height - skip - 1, -1, -1):
# read in chunks, due to the bug in the SD card libraray, avoid reading
# more than 511 bytes at once, at a performance penalty
# required if the seek offset was not a multiple of 4
                        n1 = f.readinto(b1)
                        n2 = f.readinto(b2)
                        n3 = f.readinto(b3)
                        if not n3:
                            break
                        mytft.swapcolors(b1, n1)
                        mytft.swapcolors(b2, n2)
                        mytft.swapcolors(b3, n3)
                        mytft.setXY(0, row, imgwidth - 1, row)
                        mytft.displaySCR_AS(b1, hstep)
                        mytft.displaySCR_AS(b2, hstep)
                        mytft.displaySCR_AS(b3, hstep)
                mytft.fillRectangle(0, 0, width - 1, row)
        elif mode == "data": # raw 24 bit format with rgb data (gimp type data)
            b = bytearray(width * 3)
            for row in range(height):
                n = f.readinto(b)
                if not n:
                    break
                mytft.drawBitmap(0, row, width, 1, b)
            mytft.fillRectangle(0, row, width - 1, height - 1)
        mytft.setColor(color)

def main(v_flip = False, h_flip = False):

    mytft = TFT("SSD1963", "LB04301", LANDSCAPE, v_flip, h_flip)
    width, height = mytft.getScreensize()
    mytft.clrSCR()
    mytft.backlight(99)

    if True:
        s = "0123456789"
        font = font8mono
        mytft.setTextStyle((240, 240, 240), None, 0, font)
        bfa = height % font.bits_vert + font.bits_vert
        vsa = height - bfa
        mytft.setScrollArea(0, vsa, bfa)
        mytft.setTextPos(0, height - font.bits_vert)
        mytft.printString("           This is the non-scrolling area")
        mytft.setTextPos(0, 0)
        for j in range(70):
            mytft.printString("Line {:4} ".format(j))
            for i in range(4):
                mytft.printString(s)
            mytft.printCR()      # No, then CR
            mytft.printNewline() # NL: advance to the next line
            mytft.printClrEOL()  # clear to end of line
            x,y = mytft.getTextPos()
            mytft.setTextPos(0, height - font.bits_vert)
            mytft.printString("Line {:4} ".format(j))
            mytft.setTextPos(x,y)
        mytft.printString(">")
        pyb.delay(4000)
        mytft.clrSCR()

    if True:
        mytft.setTextPos(0, 0)
        mytft.setTextStyle((255, 255, 255), None, 0, font7hex)
        mytft.printString("0123456789" * 5)
        mytft.setTextPos(0, 20)
        mytft.printString("abcdefghijklmnopqrstuvwxyz" * 2)
        pyb.delay(2000)

        mytft.setTextPos(0, 0)
        bg_buf = bytearray(dejavu14.bits_horiz * dejavu14.bits_vert * 3) # preallocate the buffer for transparency
        mytft.setTextStyle((0, 255, 0), None, 4, dejavu14)
        mytft.printString("ABCDE        NOPQRSTUVWXYZ", bg_buf)
        mytft.setTextPos(0, 40)
        mytft.setTextStyle((0, 255, 0), None, 0, dejavu14)
        mytft.printString("abcdefghijklmnopqrstuvwxyz")
        mytft.setTextPos(0, 80)
        mytft.printString("0123456789!\"$%&/()=?")
        pyb.delay(2000)

        mytft.setColor((255,255,255))
        mytft.fillClippedRectangle(200, 150, 300, 250)
        mytft.drawClippedRectangle(0, 150, 100, 250)
        pyb.delay(2000)
        mytft.clrSCR()
        cnt = 10
        mytft.setTextStyle((255,255,255), None, 0, sevensegnumfont)
        while cnt >= 0:
            mytft.setTextPos((width // 2) - 32, (height // 2) - 30)
            mytft.printString("{:2}".format(cnt))
            cnt -= 1
            pyb.delay(1000)

        gc.collect()
        mytft.clrSCR()
        buf = bytearray(5000)
        with open ("logo50.raw", "rb") as f:
            n = f.readinto(buf)
        for i in range(10):
            mytft.clrSCR()
            for cnt in range(50):
                x = pyb.rng() % (width - 51)
                y = pyb.rng() % (height - 51)
                mytft.drawBitmap(x, y, 50, 50, buf, 1)
            pyb.delay(1000)

#    os.chdir("raw_480x800")
#    files = os.listdir(".")
    files = "F0010.raw", "F0012.bmp", "F0013.data","F0011.raw"

    mytft.setTextStyle((255, 255, 255), None, 10, dejavu14)
    while True:
        for name in files:
#            name = files[pyb.rng() % len(files)]
            displayfile(mytft, name, width, height)
            mytft.setTextPos(180, 230)
            mytft.printString(name, bg_buf)
            pyb.delay(6000)

main(v_flip = False, h_flip = False)

