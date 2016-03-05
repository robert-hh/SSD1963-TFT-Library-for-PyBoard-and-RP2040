#
# Some sample code
#
import os, gc
from uctypes import addressof
from tft import *
from font import *


def odd_read(f, n):
    BLOCKSIZE = const(512) ## a sector, but may be 4 too
    part = BLOCKSIZE - (f.tell() % BLOCKSIZE) 
    if part >= n or part == BLOCKSIZE:
        return f.read(n)
    else:
        return f.read(part) + f.read(n - part)


def displayfile(mytft, name, mode, width, height):
    with open(name, "rb") as f:
        gc.collect()
        row = 0
        color = mytft.getColor()
        mytft.setColor((0, 0, 0))
        if mode == "565":
            b = bytearray(width * 2)
            for row in range(height):
                n = f.readinto(b)
                if not n:
                    break
                mytft.swapbytes(b, n)
                mytft.drawBitmap_565(0, row, width, 1, b)
            mytft.fillRectangle(0, row, width - 1, height - 1)
        elif mode == "bmp":
            f.seek(140) ## should be seek(138), but that does not work
            b = bytearray(width * 2)
            for row in range(height - 1, -1, -1):
                n = f.readinto(b)
                if not n:
                    break
                mytft.drawBitmap_565(0, row, width - 1, 1, b) # skip the last pixel
            mytft.fillRectangle(0, 0, width - 1, row)
            mytft.drawVLine(width - 1, 0, height)
        elif mode == "3x8":
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
            mytft.drawBitmap_565(x, y, 50, 50, buf)
        pyb.delay(1000)

    while True:
        displayfile(mytft, "F0010.raw", "565", width, height)
        mytft.printString(180, 230,"F0010.raw", BigFont, 2)
        pyb.delay(6000)
        displayfile(mytft, "F0011.raw", "565", width, height)
        mytft.printString(180, 230,"F0011.raw", BigFont, 2)
        pyb.delay(6000)
        displayfile(mytft, "F0012.bmp", "bmp", width, height)
        mytft.printString(180, 230,"F0012.bmp", BigFont, 1)
        pyb.delay(6000)
        displayfile(mytft, "F0013.data", "3x8", width, height)
        mytft.printString(180, 230,"F0013.data", BigFont, 2)
        pyb.delay(6000)
                
main()

