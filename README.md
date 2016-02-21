#TFT Class for a TFT with SSD1963 controller

**Description**

A Python class for controlling a graphical display with a SSD1963 controller and a 40 PIN interface, which is widely available in the electronics stores. It is a port of the great UTFT driver from Rinky-Dink Electronics, Henning Karlsen. This port uses at least 11 control lines:

- X1..X8 for data
- Y9 for Reset
- Y11 for WR
- Y12 for RS

Optionally, the follwing lines can be used:

- X10 for RD
- X3 for LED

CS of the TFT must be tied to GND. A separate supply for the TFT's Vcc should be set up, since it may consume more power than the Pyboard can supply. Before using X3 for LED, check the schematics of the display. In the versionb I have LED is the enable input of the LED power's step-up converter. But the LED input may be as well the LED power input itself, in which case you have to supply the appropriate current/voltage.

At the moment, the code is more a proof of feasibility. I have a single TFT here, so I cannot test a lot. The actual state is working with a 480x272 TFT in landscape and portrait mode. There is no principal limitation in size and mode. I just have to figure out how to set the TFT's configuration and make a smooth interface for that.

Since the number of port lines on Pyboard are limited, I use the 8 bit interface. For speed, the lower level functions are coded as viper or assembler functions. Both variants are supplied. Obviously, the Assembler versions are little bit faster, at the cost of LOC. The total advantage of using assembler may be limited. The assembler functions need 220ns to 260ns to send the three bytes of a display pixel, in contrast to the about 10 µs needed to call this function.
On the upside of his choice is, that you can supply up to 24 bit of color data.
In total, the speed is reasonable. Clearing the 480x272 display (= filling it with a fixed color) takes about 30ms. Filling it with varying patterns takes about 40 ms. Reading a 480x272 sized bitmap from a file ans showing it takes about 300 ms. Most of the time used for reading the file. Drawing a horizontal or vertical line takes about 250µs. Since most of the time is needed for set-up, the length of the line does not matter. Drawing a single Pixel at a certain coordinate takes 40µs, in contrast to the 250ns in the bulk transfers, used e.g. by clearSCR() or drawRectangle().

**Functions**
```
Create instance:

mytft = TFT(model, width, height)
    model: String with the controlle model. At the moment, "SSD1963" is the only one supported
    width: Width of the LCD in pixels. If width is less than height, landscape mode is assumed.
    height: Height of the LCD in pixels

Functions:
setColor(red, green, blue) 
    # set the foreground color, used by the draw functions, range 0..255 each; 
      the lower bits may be ignored

setBGColor(red, green, blue) 
    # set the background color, used by clrSCR(), range 0..255 each; the lower bits may be ignored

clrSCR()
    # set the total screen to the background color.

drawPixel(x, y)
    # set a pixel at position x, y with the foreground color

drawLine(x1, y2, x2, y2)
    # draw a line from x1, y1 to x2, y2. If the line is horizontal or vertical, 
      the respective functions are used. Otherwise drawPixel is used. That's where Python gets slow.

drawHLine(x, y, len)
    # draw a horizontal line from x,y of len length

drawVLine(x, y, len)
    # draw a vertical line from x,y of len length

drawRectangle(x1, y1, x2, y2)
    # draw a rectangle from x1, y1, to x2, y2. The width of the line is 1 pixel.

fillRectangle(x1, y1, x2, y2)
    # fill a rectangle from x1, y1, to x2, y2 with the foreground color.

drawBitmap(x, y, width, height, data)
    # draw a bitmap at location x, y dimension width x height. Data must contain the bitmap 
      data and must be of type bytearray or buffer. It must contain 3 bytes per 
      pixel (red, green, blue). The total size of data must be width * height * 3. 
      No type checking is performed.

drawBitmap565(x, y, width, height, data)
    # draw a bitmap at location x, y dimension width x height. Data must contain the bitmap 
      data and must be of type bytearray or buffer. It must contain 2 bytes per pixel 
      with packed color data (bbbbbggggggrrrrr) in little endian format (the byte with 
      red first). The total size of data must be width * height * 2. No type checking is performed.
      
printString(x, y, s)
    # Print a string s at location x, y using a small font. This function
      is pretty slow, because it does a lot of bit fiddling. At least some
      of it should be replaced by a viper subroutine.
    
The remaining functions are the lower level interfaces, that obviously can be used directly. 
The documentation may follow later on, some documentations is inline.
```

**To Do**
- Fiddle out the TFT controller settings about the LCD size, such that there is a robust definition of the mode. The UTFT library seems to implement stuff, that the controller would handle for you.
- Try other display sizes
- Make a nice interface for BMP type files, such that they can be displayed in a uniform matter.
- basic support for text; that could be tricky to make it efficient
- Implement some more of the basic functions (like Circle); that'll be easy, since it only uses drawPixel and drawLine

**Things beyond the horizon at the moment**
- Support the touch interface; but that could already be available somewhere - it's based on SPI
- Other Controllers

**Files:**

- tft.py: Source file with comments.
- smallfont.py: Bittpattern of a small font, Origin: Rinky-Dink Electronics, Henning Karlsen
- README.md: this one
- Sample raw bitmap file with 565 encoding (16 bits per Pixel)

**Short Version History**

**0.1** Initial release with some basic functions, limited to a 480x272 display in landscape mode and PyBoard. More a proof of feasibilty.


