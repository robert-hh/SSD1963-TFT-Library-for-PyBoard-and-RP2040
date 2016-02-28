#TFT Class for a TFT with SSD1963 controller

**Description**

A Python class for controlling a graphical display with a SSD1963 controller and a 40 PIN interface, which is widely available in the electronics stores. It is a port of the great UTFT driver from Rinky-Dink Electronics, Henning Karlsen. This port uses at least 11 control lines for the 8080-type interface style:

- X1..X8 for data
- Y9 for /Reset
- Y10 for /RD
- Y11 for /WR
- Y12 for C/D

If you only write to the display, RD (Y10) may be left open. Optionally, the follwing lines can be used:

- X3 for LED
- X4 for TFT POWER

CS of the TFT must be tied to GND. A separate supply for the TFT's Vcc should be set up, since it may consume more power than the Pyboard can supply. But it is fine to connect the input of the power regulator to PyBoard Vin, unless the TFT sips more than 1A. Then you can supply the whole unit either through USB or an external power supply at Vin and GND. Before using X3 for LED, check the schematics of the display. In the version I have LED is the enable input of the LED power's step-up converter. But the LED input may be as well the LED power input itself, in which case you have to supply the appropriate current & voltage. If you do not use X3 for LED, connect LED to the 3.3Vcc of the TFT. 
LED may also be controlled by one the SSD1963's GPIO's. But that requires resoldering a resistor on the TFT and changing the setting of the SSD1963.

At the moment, the code is a basic package. I have a two TFTs here, so I cannot test a lot. The actual state is working with a 480x272 and a 800x480 TFT in landscape and portrait mode. There is no principal limitation in size and mode, as long as the 1215k frame buffer of the SSD1963 fits. I just have to figure out how to set the TFT's configuration and make a smooth interface for that.

Since the number of port lines on Pyboard is limited, I use the 8 bit interface. With X1 to x8, these are nicely available at GPIO port A0..A7 in the right order - intentionally, I assume. For speed, the lower level functions are coded as viper or assembler functions. Both variants are supplied. Obviously, the Assembler versions are little bit faster, at the cost of LOC. The total advantage of using assembler may be limited. The assembler functions need 220ns to 260ns to send the three bytes of a display pixel, in contrast to the about 10 µs needed to call this function.
On the upside of this 8 bit interface choice is, that you can supply up to 24 bit of color data, in contrast to the 16 bit when using the 16 bit interface.
In total, the speed is reasonable. Clearing the 480x272 display (= filling it with a fixed color) takes about 30ms. Filling it with varying patterns takes about 40 ms. Reading a 480x272 sized bitmap from a file and showing it takes about 300 ms, the same for a 800x480 bitmap takes 700ms. Most of that time is needed for reading the file. Drawing a horizontal or vertical line takes about 250µs. Since most of the time is needed for set-up of the function, the length of the line does not really matter. Drawing a single Pixel at a certain coordinate takes 40µs, in contrast to the 250ns/Pixel in bulk transfers, used e.g. by clearSCR() or fillRectangle().

**Functions**
```
Create instance:

mytft = TFT(controller, lcd_type, orientation [, flip_vertical = False][, flip_horizontal = False])
    controller: String with the controller model. At the moment, "SSD1963" is the only 
                one supported
    lct_type: type of LCD. At the moment, "LB04301" (480x272, 4.3") and "AT070TN92" (800x480, 7") 
              are supported.
    orientation: which is LANDSCAPE or PORTRAIT
    flip_vertical: Flip vertical True/False
    flip_horizontal: Flip horizontal True/False

Functions:

getScreensize():
    # return a tuple of logical screen width and height

setColor(red, green, blue) 
    # set the foreground color, used by the draw functions, range 0..255 each; 
      the lower bits may be ignored

setBGColor(red, green, blue) 
    # set the background color, used by clrSCR(), range 0..255 each; 
      the lower bits may be ignored

clrSCR()
    # set the total screen to the background color.

drawPixel(x, y)
    # set a pixel at position x, y with the foreground color

drawLine(x1, y2, x2, y2)
    # draw a line from x1, y1 to x2, y2. If the line is horizontal or vertical, 
      the respective functions are used. Otherwise drawPixel is used. 
      That's where Python gets slow.

drawHLine(x, y, len)
    # draw a horizontal line from x,y of len length

drawVLine(x, y, len)
    # draw a vertical line from x,y of len length

drawRectangle(x1, y1, x2, y2)
    # draw a rectangle from x1, y1, to x2, y2. The width of the line is 1 pixel.

fillRectangle(x1, y1, x2, y2)
    # fill a rectangle from x1, y1, to x2, y2 with the foreground color.

drawCantedRectangle(x1, y1, x2, y2)
    # draw a rectangle with canted edges from x1, y1, to x2, y2. The width of the line is 1 pixel.

fillCantedRectangle(x1, y1, x2, y2)
    # fill a rectangle with canted edges from x1, y1, to x2, y2 with the foreground color.

drawCircle(x, y, radius)
    # draw a circle at x, y with radius diameter. The width of the line is 1 pixel.

fillCircle(x, y, radius)
    # draw a filled circle at x, y with radius diameter.

drawBitmap(x, y, width, height, data)
    # draw a bitmap at location x, y dimension width x height. Data must contain 
      the bitmap data and must be of type bytearray or buffer. It must contain 
      3 bytes per pixel (red, green, blue). The total size of data must be 
      width * height * 3. No type checking is performed.

drawBitmap565(x, y, width, height, data)
    # draw a bitmap at location x, y dimension width x height. Data must contain
      the bitmap data and must be of type bytearray or buffer. It must contain 
      2 bytes per pixel with packed color data (bbbbbggggggrrrrr) in little endian 
      format (the byte with red first). The total size of data must be 
      width * height * 2. No type checking is performed.
      
printString(x, y, s , font [, fgcolor = None ][, bgcolor = None])
    # Print a string s at location x, y using the font given in font.
      The actual choices are SmallFont, BigFont or SevenSegNumFont. If fgcolor 
      is given, that color is used for the characters. If bgcolor is given, 
      that color is used for the background. Default are colors set by 
      setColor() and setBGColor(). FGcolor and BGcolor must be triples 
      that can be converted to a bytearray, e.g. tuples, lists or strings.

----- lower level functions ---

setXY(x1, y1, x2, y2)
    # set the region for the bulk transfer functions fillSCR() and displaySCRxx()
    
clrXY()
    # set the bulk transfer region back to the full screen size
    
fillSCR(data, size)
fillSCR_AS(data, size)
    # fill the region set with setXY() or clrXY() with the pixel value given
      in data. Size is the number of pixels, data must be a bytearray object
      of three bytes length with the red-green-blue values. The version with
      the AS suffix uses inline-assembler.
          
displaySCR(data, size)
displaySCR_AS(data, size)
    # fill the region set with setXY() or clrXY() with the pixel values given
      in data. Size is the number of pixels, data must be a bytearray object
      of 3 * size length with the red-green-blue values per pixel. The
      version with the AS suffix uses inline-assembler.
    
          
displaySCR565(data, size)
displaySCR565_AS(data, size)
    # fill the region set with setXY() or clrXY() with the pixel values given
      in data. Size is the number of pixels, data must be a bytearray object
      of 2 * size length with the 16 bit packed red-green-blue values per pixel.
      The color pattern per word is bbbbbggggggrrrrr, with rrrrr in the lower 
      (=first) byte. The version with the AS suffix uses inline-assembler.

tft_cmd_data(cmd, data, size)
tft_cmd_data_AS(cmd, data, size)      
    # Send a command byte and data to the controller. cmd is a single integer
      with the command, data a bytearray of size length with the command payload.  
      The version with the AS suffix uses inline-assembler.
      During start-up of the tft, when the device is clocked by the 10MHz or 
      6.5 MHz crystal, the assembler version is a little bit too fast.
      Please use the viper version instead.
      This function may also be used for other displays like the Character based
      2x20 or 4x20 displays, which use the 8080-type interface.

tft_cmd(cmd)
    # send a single command byte to the tft.
      
tft_data(cmd, data, size)
tft_data_AS(cmd, data, size)
    # Send data to the tft. Size is the number of bytes, data must be 
      a bytearray object size length. The version with the AS suffix uses
      inline-assembler.

tft_read_data(cmd, data, size)
    # Send a command to the tft and get the response back. cmd is the command byte, 
      data a bytearray of size length which will receive the data.
      
```
**Fonts**
A font is defined a bytes string or byte array with a fixed amount of data per character. The first four bytes define the characteristics:
Offset 0: Columns - Pixel width of the font
Offset 1: Rows - Pixel height of the font
Offset 2: Ordinal number of the first character in the font. Typically this is 0x20 (space)
Offset 3: Number of character in the font set.
Each Character is defined by ((Columns + 7) // 8) * rows bytes, row by row. Each Character pixel row must consist of a full number of bytes. For instance 12 columns require 2 bytes per row. If a character is not in the font set, usually the first character of the set is printed.

**To Do**
- Try other display sizes

**Things beyond the horizon at the moment**
- Other text fonts
- Support the touch interface; but that could already be available somewhere
- Some experiments with LCD settings
- Other Controllers

**Files:**
- tft.py: Source file with comments.
- font.py: Bitpattern of a three fonts, Origin: Rinky-Dink Electronics, Henning Karlsen
- dummyfont.py: Dummy versions of the three fonts, which just define a single char as placeholder
- README.md: this one
- *.raw: Sample raw bitmap files with 565 encoding (16 bits per Pixel)

**Short Version History**

**0.1** 
Initial release with some basic functions, limited to a 480x272 display in landscape mode and PyBoard. More a proof of feasibilty.

**0.2** 
Established PORTRAIT and LANDSCAPE mode. Added printString(), drawCircle() and fillCircle()

**0.3** 
- Font widths do not have to be a multiple of 8 any more. 
- Added drawCantedRectangle() and fillCantedrectangle(). 
- Changed the arguments of the constructor to name the controller and lcd type instead of controller and dimensions. The lcd type defines the size, the default orientation and the required initialization code. 
- Provided a dummy font.

**0.4** (no real changes to the TFT class)
- Some explanations on how to determine the LCD settings of the SSD1963 from the LCD data sheet, embedded in the source file.
- The graphic file conversion for displaying as a RGB data bitmap is nicely done by Gimp, the Swiss Army Knife of graphics. Just export the picture as raw data!

