#
# Some sample code
#
import os, gc
from uctypes import addressof
from tft import *
from font import *
from struct import unpack

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
                mytft.swapbytes(b, n)
                margin = (width - imgwidth) // 2
                if margin: ## picure with less than frame
                    mytft.drawHLine(0, row, margin)
                    mytft.drawHLine(imgwidth + margin, row, margin)
                mytft.drawBitmap(margin, row, imgwidth, 1, b, 1)
            mytft.fillRectangle(0, row, width - 1, height - 1)
        elif mode == "bmp":  # Windows bmp file
            BM, filesize, res0, offset = unpack("<hiii", f.read(14))
            hdrsize, imgwidth, imgheight, planes, colors = unpack("<iiihh", f.read(16))
            if colors in (16, 24) and imgwidth <= width: ## only 16 or 24 bit colors supported
                bytes_per_pix = colors // 8
                offset += 6
                f.seek(offset)
                b = bytearray(imgwidth * bytes_per_pix)
                for row in range(height - 1, -1, -1):
                    n = f.readinto(b)
                    if not n:
                        break
                    margin = ((width - imgwidth) // 2) + 1
                    if margin: ## picure with less than frame
                        mytft.drawHLine(0, row, margin)
                        mytft.drawHLine(imgwidth - 1 + margin, row, margin)
                    if colors == 16: ## 16 bit bmp data
                        mytft.drawBitmap(margin, row, imgwidth - 1, 1, b, 1)
                    else: ## 24 bit bmp has bgr data
                        mytft.swapcolors(b, n)
                        mytft.drawBitmap(margin, row, imgwidth - 1, 1, b)
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
    if True:    
        mytft.printString(10, 20, "0123456789" * 5, SmallFont, 0, (255,0,0))
        mytft.printString(10, 40, "0123456789" * 5, SmallFont, 0, (255,0,0))
        pyb.delay(2000)

        mytft.printString(10, 20, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", BigFont, 2, (0, 255, 0))
        mytft.printString(10, 60, "abcdefghijklmnopqrstuvwxyz", BigFont, 0, (0, 255, 0))
        mytft.printString(10, 100, "0123456789!\"§$%&/()=?", BigFont, 0, (0, 255, 0))
        pyb.delay(2000)

        mytft.setColor((255,255,255))
        mytft.fillClippedRectangle(200, 150, 300, 250)
        mytft.drawClippedRectangle(0, 150, 100, 250)
        pyb.delay(2000)
        mytft.clrSCR()
        cnt = 10
        while cnt >= 0:
            mytft.printString((width // 2) - 32, (height // 2) - 30, "{:2}".format(cnt), SevenSegNumFont)
            cnt -= 1
            pyb.delay(1000)
        gc.collect()
        mytft.clrSCR()
        buf = bytearray(5000)
        with open ("logo50.raw", "rb") as f:
            n = f.readinto(buf)
        mytft.swapbytes(buf, n)

        for i in range(10):
            mytft.clrSCR()
            for cnt in range(50):
                x = pyb.rng() % (width - 51)
                y = pyb.rng() % (height - 51)
                mytft.drawBitmap(x, y, 50, 50, buf, 1)
            pyb.delay(1000)

    files = "F0010.raw", "F0012.bmp", "F0013.data","F0011.raw"

    while True:
        name = files[pyb.rng() % len(files)]
        displayfile(mytft, name, width, height)
        mytft.printString(180, 230,name, BigFont, 2)
        pyb.delay(6000)
                
main()

