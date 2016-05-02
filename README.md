**TFT Class for a TFT with SSD1963 controller**
===============================================

# Description and physical interface

A Python class for controlling a graphical display with a SSD1963 controller
and a 40 PIN interface, which is widely available in the electronics stores.
It is a port of the great UTFT driver from Rinky-Dink Electronics, Henning Karlsen.
This port uses at least 11 control lines for the 8080-type interface style:

|PyBoard|TFT Pin|Function|Comment|
|:---|:---|:---|:---|
|X1..X8|21..28|D0..D7|Data port|
|Y9|17|/Reset| |
|Y10|6|/RD|Only when reading is required|
|Y11|5|/WR||
|Y12|4|C/D| |
|X3|19|LED|Tie TFT input to Vcc if switching is not required|
|X4|-|TFT Vcc On/Off|Requires external circuitry|  

If you only write to the display's frame buffer, RD (Y10) may be left open, but
then the transparency modes of printChar() do not work any more. The pulse
widths of /WR and /RD are rather small. Do not use long connections.

CS of the TFT must be tied to GND. A separate supply for the TFT's Vcc should
be set up, since it may consume more power than the Pyboard can supply. But it
is fine to connect the input of the power regulator to PyBoard's Vin resp. V+,
unless the TFT sips more than 1A. Then you can supply the whole unit either
through USB or an external power supply at Vin and GND. Before using X3 for
LED, check the schematics of the display. In the version I have LED is the
enable input of the backlight LED power's step-up converter. But the LED input
may be as well the LED power input itself, in which case you have to supply the
appropriate current & voltage. If you do not use X3 for LED, connect LED to
the 3.3Vcc of the TFT. LED may also be controlled by one the SSD1963's GPIO's.
But that requires resoldering a resistor on the TFT and changing the setting
of the SSD1963.

At the moment, the code is a basic package. I have a two TFTs here, so I
cannot test a lot. The actual state is working with a 480x272 and a 800x480 TFT
in landscape and portrait mode. There is no principal limitation in size and
mode, as long as the 1215k frame buffer of the SSD1963 fits. I just have to
figure out how to set the TFT's configuration and make a smooth interface for that.

Since the number of port lines on Pyboard is limited, I use the 8 bit
interface. With X1 to x8, these are nicely available at GPIO port A0..A7 in
the right order - intentionally, I assume. For speed, the lower level functions
are coded as viper or assembler functions. Obviously, the Assembler versions
are little bit faster, at the cost of LOC. The total advantage of using
assembler may be limited. The assembler functions need 220ns to 260ns to send
the three bytes of a display pixel, in contrast to the about 4 µs needed to call this function. On the upside of this 8 bit interface choice is, that you can supply
 up to 24 bit of color data, in contrast to the 16 bit when using the 16 bit interface.

In total, the speed is reasonable. Clearing the 480x272 display (= filling it
with a fixed color) takes about 25ms. Filling it with varying patterns
takes about 40 ms. Reading a 480x272 sized bitmap from a file and showing
it takes about 250 to 350ms, depending on the speed of the SD card, the same
for a 800x480 bitmap takes 500 to 700ms. Most of that time is needed for
reading the file. Drawing a horizontal or vertical line takes about 250µs.
Since most of the time is needed for set-up of the function, the length of
the line does not really matter. Drawing a single Pixel at a certain
locations takes 9µs, in contrast to the 250ns/Pixel in bulk transfers,
used e.g. by clearSCR() or fillRectangle().


# Class TFT

## High level functions

### Create instance

**mytft = TFT(controller, lcd_type, orientation [, flip_vertical = False][, flip_horizontal = False])**  
Create an instance of the tft class, initialize the controller and clear the screen. Parameters:  
**controller**: String with the controller model. At the moment, "SSD1963" is the only one supported  
**lcd_type**: type of LCD. At the moment, "LB04301" (480x272, 4.3") and "AT070TN92" (800x480, 7") are supported.  
**orientation**: which is LANDSCAPE or PORTRAIT  
**flip_vertical**: Flip vertical True/False  
**flip_horizontal**: Flip horizontal True/False  

### Functions:

**tft_init(controller, lcd_type, orientation [, flip_vertical = False][, flip_horizontal = False])**  
Repeat the initialization which was peformed during creation of the instance.  
This function must be called if the TFT power was switched off, but PyBoard
kept  on running. tft_init is called by __init__() during the creation of the
instance. It includes the call to power(True), but leaves the backlight off!

**getScreensize()**  
Return a tuple of logical screen width and height.

**setColor(FGcolor)**  
Set the default foreground color, used by the draw and print functions.
**FGcolor** must be a 3-element tuple with the values for red, green and blue,
range 0..255 each; the lower bits may be ignored.

**setBGColor(BGcolor)**  
Set the default background color, used by clrSCR() and other functions.
**BGcolor** must be a 3-element tuple with the values for red, green and blue
in the range 0..255 each; the lower bits may be ignored.

**getColor()**  
Get the default foreground color, set by a previous setColor() call.

**getBGColor()**  
Get the default background color, set by a previous setBGColor() call.

**set_tft_mode([v_flip = False,][ h_flip = False,][ c_flip = False, ][orientation = LANDSCAPE])**   
Set the operation mode of the tft, equivalent to the settings used at init time. Parameters:  
**orientation**: which is LANDSCAPE or PORTRAIT.  
**v_flip**: Flip vertical True/False  
**h_flip**: Flip horizontal True/False  
**c_flip**: exchange red/blue.  
These changes are effective for the whole screen once set.

**get_tft_mode()**  
Gets the 4 element tuple of v_flip, h_flip, c_flip and orientation.

**clrSCR([color = None)**  
Set the total screen to the background color, set the scroll area back to the
full screen and set the text print position to (0,0). The optional parameter
**color** specifies the color to be used for clearing. If not set the color
specified by setBGColor() is taken. If only the scrollable area is to be
cleared, use **printClrSCR()**.

**backlight(percent)**  
Set the LED backlight brightness to percent (0..100). 0 means backlight off.
This function requires the LED-A pin of the TFT to be connected to Y3.

**power(Switch)**  
Switch the power of the TFT on (Switch == True) or off (Switch = False). After
turning power on again, the init process has to be repeated, e.g. by a call
to **init()**. This function requires Y4 to be connected to an appropriate circuit.

**drawPixel(x, y, color)**  
 Set a pixel at position **x**, **y** with the color **color**, which must be
 a bytearray or bytes object of 3 bytes length with the color setting for
 red, green and blue.

**drawLine(x1, y2, x2, y2 [, color = None])**  
Draw a line from **x1**, **y1** to **x2**, **y2**. If the line is horizontal
or vertical, the respective functions are used. Otherwise drawPixel() is used.
The optional parameter **color** specifies the color to be used. If not set
the color specified by setColor() is taken.

**drawHLine(x, y, len [, color = None])**
Draw a horizontal line from **x**,**y** of **len** length.
The optional parameter **color** specifies the color to be used. If not set
the color specified by setColor() is taken.

**drawVLine(x, y, len [, color = None])**  
Draw a vertical line from **x**,**y** of **len** length
The optional parameter **color** specifies the color to be used. If not set
the color specified by setColor() is taken.

**drawRectangle(x1, y1, x2, y2 [, color = None])**  
Draw a rectangle from **x1**, **y1** to **x2**, **y2**. The width of the line
is 1 pixel. The optional parameter **color** specifies the color to be used.
If not set the color specified by setColor() is taken.

**fillRectangle(x1, y1, x2, y2[, color = None])**  
Fill a rectangle from **x1**, **y1** to **x2**, **y2** with the foreground
color or with the color given in the optional argument **color**.

**drawClippedRectangle(x1, y1, x2, y2 [, color = None])**  
Draw a rectangle with canted edges from **x1**, **y1** to **x2**, **y2**. The
width of the line is 1 pixel. The optional parameter **color** specifies the
color to be used. If not set the color specified by setColor() is taken.

**fillClippedRectangle(x1, y1, x2, y2, [, color = None])**  
Fill a rectangle with canted edges from **x1**, **y1** to **x2**, **y2** with
the foreground color. The optional parameter **color** specifies the color
to be used. If not set the color specified by setColor() is taken.

**drawCircle(x, y, radius, [, color = None])**  
Draw a circle at **x**, **y** with **radius** radius. The width of the line
is 1 pixel. The optional parameter **color** specifies the color to be used.
If not set the color specified by setColor() is taken.

**fillCircle(x, y, radius [, color = None])**  
Draw a filled circle at **x**, **y** with **radius** radius. The optional
parameter color specifies the **color** to be used. If not set the color
specified by setColor() is taken.

**drawBitmap(x, y, width, height, data, bits=24 [, colortable])**  
Display a bitmap at location **x**, **y** and dimension **width** x **height**.
**data** must contain the bitmap data and must be of type bytearray or buffer.
**bits** tells how many bits per pixel the data must have:  

* bits = **1**: The data must contain 1 bit per pixel. The colors to be use  must
be supplied in the colortable, 4 bytes per value in the order
blue, green, red, 0. If colortable is None, the values for color and
BGcolor are used. This matches the BMP file type with 1 bit per pixel.
The total size of data must be width \* height / 8.
* bits = **2**: The data must contain 2 bits per pixel. The colors to be used
must be supplied in the colortable, 4 bytes per value in the order
blue, green, red, 0. The total size of data must be width \* height / 4.
* bits = **4**: The data must contain 4 bits per pixel. The colors to be used
must be supplied in the colortable, 4 bytes per value in the order
blue, green, red, 0. This matches the BMP file type with 4 bits per pixel.
The total size of data must be width \* height / 2.
* bits = **8**: The data must contain one byte per pixel. The colors to be used
must be supplied in the colortable, 4 bytes per value in the order
blue, green, red, 0. This matches the BMP file type with 8 bits per pixel
The total size of data must be width \* height.
* bits = **16**: The data must contain 2 bytes per pixel with packed color
data (rrrrrggggggbbbbb) in little endian format (the byte with blue first).
This order matches the 16 bit BMP file type. The total size of data must be
width \* height \* 2.
* bits = **24** (default): The data must contain 3 bytes per pixel
(blue, green, red), which matches the 24 bit BMP file type.
The total size of data must be width \* height \* 3.

No type or size checking of the **data** or **colortable**  is performed.

**setTextPos(x, y[, clip = 0][, scroll = True])**  
Set the starting position for the following calls of  printString() and
printChar() to **x**, **y.** x, y is the position of the leftside top pixel of
the first character using the font given in font. **clip** defines, if set, the
 maximal length which will be printed. The default is the  screen width.
 **scroll** tells, whether text will flow over to a next line if longer than
 the screen width or the width given by the clip parameter. The default is True.

**getTextPos()**  
Return a tuple with the actual x,y values of the text postion for the next char
to be printed.

**setTextStyle(fgcolor = None , bgcolor = None, transparency = 0, font = dummyfont, gap = 0)**  
Set the Style used for text printing with printChar() and printString().  
If **fgcolor** is given, that color is used for the characters.
If **bgcolor** is given, that color is used for the background.
For transparency the following values are valid:

- 0: no transparency. The bgcolor is used for character background, fgcolor for the text
- 1: 50% transparency. The previous background is kept, but 50% dimmed
- 2: full transparency. The previous background is kept.
- 4: the existing background will be inverted
- 8: for the foreground color, each background pixel value is inverted.

The foreground setting can be combined with any of the background settings.
Default are colors set by setColor() and setBGColor().
**fgcolor** and **bgcolor** must be triples that can be converted to a
bytearray, e.g. tuples, lists or strings. The font used must be created e.g.
using the GLCD tool and then converted using the cfonts_to_packed_py.py
script of Peter Hinch, adapted to the needs of this library.
**gap** specifies additional spacing between the characters.

**getTextStyle()**  
Return a tuple of fgcolor, bgcolor, transparency, font and gap.

**printString(s [, buffer])**  
Print the string **s** at the location set by setTextPos() in the style
detailed by setTextStyle(). **buffer**  is a optional argument for a buffer
receiving the background data when transparency is chosen. The size must be at
least char_width * char_heigth * 3 of the selected font. These values can be
determined with the **font.properties()** function (see below). There is no
size checking involved. If the buffer is too small, the program (and PyBoard)
will crash. printString() advances the text position for the next text by
the width of the character. It will flow over to a next line, if necessary
and enabled by setTextPos(), at a distance given by the char height.
Before printing text, the font must be set with setTextStyle().
printString() returns pixel length of printed string.

**printChar(c [, buffer])**  
Print the character **c** at the location set by setTextPos() in the style
detailed by setTextStyle(). **buffer**  is a optional argument for a buffer
receiving the background data when transparency is chosen. The size must be at
least char_width * char_heigth * 3 of the selected font. These values can be determined
with the **font.properties()** function (see below). There is no size checking involved.
If the buffer is too small, the program (and PyBoard) will crash.
printString() advances the text position for the next text by the width of the
character. It will flow over to a next line, if necessary and enabled by
setTextPos(), at a distance given by the char height. Before printing text,
the font must be set with setTextStyle(). printChar() returns
pixel width of printed string.

**printNewline([clear = False])**  
Advance the string text position to the next line, where the line height is
given by the selected font. If **clear** is True, clear this line.

**printCR()**  
Set the text position to the start of the line.

**printClrSCR()**  
Clear the scrollable window set by setScrollArea() with the background color
set by setTextStyle(). The text position and the logical first line is set to
the start of the physical first line of that area.

**printClrLine(mode = 0)**  
Clear the actual line depending on the value of the **mode** argument:  
0: Clear to the end of the line  
1: Clear to the beginning of the line  
2: Clear the entire line  
The text background color and the height given by the selected font.

**setScrollArea(top_fixed_area,  vertical_scroll_area, bottom_fixed_area)**  
Define the area for scrolling.  **top_fixed_area** tells the number of lines
at the top which are not scrolled, **vertical_scroll_area**: the number of
lines which will be scrolled, and **bottom_fixed_area** the number of lines
at the bottom which are not scrolled.

**setScrollStart(line)**  
Set the **line** which will be the one display first in the vertical scroll area.
Screen coordinates are always physical coordinates.



## Lower level functions

**setXY(x1, y1, x2, y2)**  
Set the region for the bulk transfer functions fillSCR() and displaySCRxx()
to **x1**, **y1** up to and including **x2**, **y2**

**clrXY()**  
Set the bulk transfer region back to the full physical screen size.

**TFT_io.fillSCR_AS(data, size)**  
Fill the region set with setXY() or clrXY() with the pixel value given
in **data**. **size** is the number of pixels, which must match the previous
settings as (x2 - x1 + 1) \* (y2 - y1 + 1). **data** must be a bytearray
object of three bytes length with the red-green-blue values.

**TFT_io.displaySCR_AS(data, size)**  
Fill the region set with setXY() or clrXY() with the pixel values given
in **data**. **size** is the number of pixels, which must match the previous
settings as (x2 - x1 + 1) \* (y2 - y1 + 1). **data** must be a bytearray
object of 3 * size length with the red-green-blue values per pixel.

**TFT_io.displaySCR565_AS(data, size)**  
Fill the region set with setXY() or clrXY() with the pixel values given
in data. **size** is the number of pixels, which must match the previous
settings as (x2 - x1 + 1) \* (y2 - y1 + 1). **data** must be a bytearray object
of 2 * size length with the 16 bit packed red-green-blue values per pixel.
The color pattern per word is rrrrrggggggbbbbb, with rrrrr in the lower (=first) byte.

**TFT_io.displaySCR_fontbitmap(bitmap: ptr8, size: int, control: ptr8, bg_buf: ptr8)**  
Fill the region set with setXY() with the pixel values given
in bitmap. **bitmap** contains a single bit per pixel . The highest order bit
in a byte is the first to be displayed. **size** is the number of bits the
bitmap. **control** is a byte vector with further parameters controlling the
behavior, packed here,  since viper functions allow 4 arguments only.  

Bytes 0..2: Background color, which is used for a bit value of 0  
Bytes 3..5: Foreground color, which is used for a bit value of 1  
Byte 6: Transparency mode. See setTextStyle for the value definition   

**bg_buf** must contain the frame buffer data for the pixel area chose. It is
used only when the respective transparency mode is choses. If not used,
an empty bytearray must be supplied. No size checking is performed.

**TFT_io.displaySCR_bmp(bitmap: ptr8, size: int, bits: ptr8, colortable: ptr8)**  
Fill the region set with setXY() with the pixel values given
in **bitmap**. The number of bits per pixel is defined by **bits**. Suitable
values are 1, 2, 4, and 8. **size** tells the number of pixel data items in bitmap.
**colortable** must contain the color matching to the respective value of
a pixel with 4 bytes per value in the order blue, green, red, d/c.
The fourth byte is ignored. Therefore, the expected sizes of colortable are
8, 16, 64 or 1024 bytes. No size checking is performed on bitmap or colortable.
If not the full range of values is used for the pixels, the colortable may be smaller.

**TFT_io.tft_cmd_data(cmd, data, size)**  
**TFT_io.tft_cmd_data_AS(cmd, data, size)**  
 Send a command byte and data to the controller. **cmd** is a single integer
 with the command, **data** a bytearray of size length with the command payload.
 The version with the AS suffix uses inline-assembler. During start-up of the
 TFT, when the device is clocked by the 10MHz or  6.5 MHz crystal, the assembler
 version is a little bit too fast. Please use the viper version instead.
 This function may also be used for other displays like the character
 based 2x20 or 4x20 displays, which use a 8080-type interface.

**TFT_io.tft_cmd(cmd)**  
Send a single command byte to the TFT.

**TFT_io.tft_data_AS(cmd, data, size)**  
Send data to the TFT. **size** is the number of bytes, **data** must be a
bytearray object of **size** length.

**TFT_io.tft_read_cmd_data_AS(cmd, data, size)**  
Send a command to the TFT and get the response back. **cmd** is the command byte,
**data** a bytearray of **size** length which will receive the data. This
function can be used to read status data or to read data from the frame buffer.
In the latter case, the region to be read from must be specified first with a
call to setXY(). Please remind, that **size** specifies the number of bytes to
be received, which is 3 * number_of_pixels, if data from the frame buffer is read.

**TFT_io.swapbytes(data, size)**  
Swap byte pairs in **data**. Data must contains **size** bytes. This helper
function may be used for 565 coded data, when the order of the bytes is wrong.

**TFT_io.swapcolors(data, size)**  
Swap the first and third byte in byte triples of **data**. Data must contain
**size** bytes. This helper function may be used for 24 bit colr data to
exchange blue and red


# Class TFTfont

Fonts used by the TFT lib are instances of a class. They are created in two steps:

1. Use GLCD font converter of MicroElectronica
[http://www.mikroe.com/glcd-font-creator/](http://www.mikroe.com/glcd-font-creator/)
to convert an ttf or otf font into a C data file. Take care to export the C variant.
The free version may not allow to store the file directly. Then make use of the
option 'Copy to Clipboard'. By default, the character values 32 to 127 are
converted. You may extend that. There is a bug in the tool appearing when you start at
char 0. Then, only the first char will be exported. If you like to include 0,
you have to do two steps (char 0 and char 1..xx) and combine the output manually.

2.  Use the script cfont_to_packed_py.py to convert the C-file ouput of GLCD
into a python script, containing the font class, e.g.  
`./cfont_to_packed_py.py font12.c -o font12.py`  
If your character set does not start with the space character, you have to manually add
another argument to the creation of the instance, which is the ordinal value of
the first char in the font.

The resulting python file can be imported to your code, defining font names, e.g.  
`from font12 import font12`  
The font class exports three functions:

**TFTfont(fontbitmap, index, vert, hor, no_of_chars [, first_char=32])**  
This creates the instance of the font. Parameters are:  
**fontbitmap**:  the data array with the pixel data  
**index**: an index array with the offsets of the character bitmaps to the
start of the array  
**vert**: the vertical size of the font in pixels  
**hor**: the largest horizontal size of the font in pixels. For
proportionally spaced fonts this value may differ for every characters  
**no_of_chars**: the number of characters defined in this font  
**first_char**: the ordinal value of the first characted in the font.
Default is 32 (Space)

**get_char(c)**  
Return the character bitmap and dimensions. **c** is the ordinal value of the
character. The return value is a tuple comprising of:  
**bitmap**: The address of a packed bitmap defining character pixels
row-by-row. Taken as Python object, this is an int, to be seen by a viper or
assembler function as a ptr8 data type.  
**vert**: The vertical size of the character  
**hor**:  the horizontal size of the character  
The total number of bits in the character bitmap is n = vert*hor.

**get_properties()**  
Return a tuple with the basic properties of the font. These are:  
**bits_vert**: the number of vertical pixels  
**bits_hor**: the largest number of horizontal pixels. For monospaced fonts,
this applies to all characters  
**nchar**: the number of characters in the font set  
**firstchar**: the ordinal number of the first character in the font set


# Files

- tft.py: Source file with comments. This part may be put into flash as frozen bytecode
- TFT_io.py: lower level viper and assembler functions
- TFTfont.py: Font class template, used by the font files. Freezable.
- fonts/\*: Sample fonts and the tool to convert the output of the GLCD-program
into files needed by this library. All fonts can be stored in frozen bytecode.
- README.md: this one
- tft_test.py: Sample code using the tft library
- vt100.py: Sample code with a VT100 terminal emulation function.
- \*.raw, \*.data, \*.bmp: Sample bitmap files with
    * 565 encoding (16 bits per Pixel) (\*.raw),
    * 24 bits per Pixel raw data, generated with Gimp export raw (\*.data), and
    * windows bitmap files with 1, 4, 8, 16 or 24 colors (\*.bmp). The tft_test.py script shows how to display them on the TFT.
- TFT_Adaper_for_PyBoard_3.zip: A PCB sketch for an adapter PCB, created with KiCad, including a PyBoard module.

# Remarks
**To Do**
- Cleaning up the code

**Things beyond the horizon at the moment**
- Try other display sizes than 480x272 and 800x480
- Other Controllers

# Short Version History

**0.1** Initial Release
Initial release with some basic functions, limited to a 480x272 display in landscape mode and PyBoard. More a proof of feasibilty.

**0.2** Portrait and Landscape mode

- Established PORTRAIT and LANDSCAPE mode.
- Added printString(), drawCircle() and fillCircle()

**0.3** Added more functions

- Font widths do not have to be a multiple of 8 any more.
- Added drawCantedRectangle() and fillCantedrectangle().
- Changed the arguments of the constructor to name the controller and lcd type instead of controller and dimensions. The lcd type defines the size, the default orientation and the required initialization code.
- Provided a dummy font.

**0.4** (no real changes to the TFT class)

- Some explanations on how to determine the LCD settings of the SSD1963 from the LCD data sheet, embedded in the source file.
- The graphic file conversion for displaying as a RGB data bitmap is nicely done by Gimp, the Swiss Army Knife of graphics. Just export the picture as raw data!

**0.5** Split up files

- Split up the class files and the font files
- Some testing and fixing of little bugs
- Changed the byte order in drawBitmap_565(), displaySCR565 and displaySCR565_AS. Now it is consistent to the bmp 65k color file type.

**0.6** Changed to the PCB Layout and Backlight

- added two functions to switch BG LED and power on/off, just to encapsulate these.
- added two variants of the PCB sketches. The 3rd variant uses a pair of transistors to switch the power
on and off, instead of the special power regulator which seems hard to get.
- moved the connection to the touchpad to other ports, such that both UART1 and SPI2 stay available.

**0.7** Changed text printing and font handling completely, with the kind cooperation of Peter Hinch

- changed the text print method, which requires now three functions calls, setTextStyle(), setTextPos()
and printString() or printChar()
- changed backlight(on/off) to backlight(brightness)
- some minor changes to the interface PCB layout

**0.8** Added some functions for a scrollable and fixed area and some more text print support

- added setScrollArea() and setScrollStart()
- added getTextStyle, printClrLine(), printClrSCR(), printCR(), printNewline()
- improved the speed of drawPixel() and setXY()
- some minor changes to the interface PCB layout

**0.9** Optional color parameter to all drawing functions

- Optional color parameter to all drawing functions
- Support of 1, 4 and 8 bit color depth of bmp data.
- changed getTextStyle() such that is matches setTextStyle()
