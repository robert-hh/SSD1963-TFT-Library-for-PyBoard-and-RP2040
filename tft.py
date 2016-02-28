#
# Class supporting TFT LC-displays with a parallel Interface
# First example: Controller SSD1963
# This is more or less a port of the UTFT-Library of Rinky-Dink Electronics
# to Python/Pyboard
# It uses X1..X8 for data and Y3, Y9, Y10, Y11 and Y12 for control signals.
# The minimal connection just for writes is X1..X8 for data, Y9 for /Reset. Y11 for /WR and Y12 for /RS
# Then LED and /CS must be hard tied to Vcc and GND, and /RD is not used.
#
import pyb, stm
from font import *

# define constants
#
RESET  = const(1 << 10)  ## Y9
RD     = const(1 << 11)  ## Y10
WR     = const(0x01)  ## Y11
D_C    = const(0x02)  ## Y12

LED    = const(1 << 8) ## Y3
POWER  = const(1 << 9) ## Y4

## CS is not used and must be hard tied to GND

PORTRAIT = const(0)
LANDSCAPE = const(1)

class TFT:
    
    def __init__(self, controller = "SSD1963", lcd_type = "LB04301", orientation = LANDSCAPE,  v_flip = False, h_flip = False):
        self.tft_init(controller, lcd_type, orientation, v_flip, h_flip)
    
    def tft_init(self, controller = "SSD1963", lcd_type = "LB04301", orientation = LANDSCAPE,  v_flip = False, h_flip = False):
#
# For convenience, define X1..X1 and Y9..Y12 as output port using thy python functions.
# X1..X8 will be redefind on the fly as Input by accessing the MODER control registers 
# when needed. Y9 is treate seperately, since it is used for Reset, which is done at python level
# since it need long delays anyhow, 5 and 15 ms vs. 10 µs.
#
        self.controller = controller
        self.lcd_type = lcd_type
        self.orientation = orientation
        
        self.setColor(255, 255, 255) # set FG color to white as can be.
        self.setBGColor(0, 0, 0)     # set BG to black
# special treat for BG LED
        self.pin_led = pyb.Pin("Y3", pyb.Pin.OUT_PP)
        self.pin_led.value(0)  ## switch BG LED off

        for pin_name in ["X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", 
                   "Y10", "Y11", "Y12"]:
            pin = pyb.Pin(pin_name, pyb.Pin.OUT_PP) # set as output
            pin.value(1)  ## set high as default
# special treat for Reset
        self.pin_reset = pyb.Pin("Y9", pyb.Pin.OUT_PP)
# Reset the device
        self.pin_reset.value(1)  ## do a hard reset
        pyb.delay(10)
        self.pin_reset.value(0)  ## Low
        pyb.delay(20)
        self.pin_reset.value(1)  ## set high again
        pyb.delay(20)
#
# Now initialiize the LCD
# This is for the SSD1963 controller and two specific LCDs. More may follow.
# Data taken from the SSD1963 data sheet, SSD1963 Application Note and the LCD Data sheets
#
        if controller == "SSD1963":           # 1st approach for 480 x 272
            self.tft_cmd_data(0xe2, bytearray(b'\x1d\x02\x54'), 3) # PLL multiplier, set PLL clock to 100M
              # N=0x2D for 6.5MHz, 0x1D for 10MHz crystal 
              # PLLClock = Crystal * (Mult + 1) / (Div + 1)
              # The intermediate value Crystal * (Mult + 1) must be between 250MHz and 750 MHz
            self.tft_cmd_data(0xe0, bytearray(b'\x01'), 1) # PLL Enable
            pyb.delay(10)
            self.tft_cmd_data(0xe0, bytearray(b'\x03'), 1)
            pyb.delay(10)
            self.tft_cmd(0x01)                     # software reset
            pyb.delay(10)
#
# Settings for the LCD
# 
# The LCDC_FPR depends on PLL clock and the reccomended LCD Dot clock DCLK
#
# LCDC_FPR = (DCLK * 1048576 / PLLClock) - 1 
# 
# The other settings are less obvious, since the definitions of the SSD1963 data sheet and the 
# LCD data sheets differ. So what' common, even if the names may differ:
# HDP  Horizontal Panel width (also called HDISP, Thd). The value store in the register is HDP - 1
# VDP  Vertical Panel Width (also called VDISP, Tvd). The value stored in the register is VDP - 1
# HT   Total Horizontal Period, also called HP, th... The exact value does not matter
# VT   Total Vertical Period, alco called VT, tv, ..  The exact value does not matter
# HPW  Width of the Horizontal sync pulse, also called HS, thpw. 
# VPW  Width of the Vertical sync pulse, also called VS, tvpw
# Front Porch (HFP and VFP) Time between the end of display data and the sync pulse
# Back Porch (HBP  and VBP Time between the start of the sync pulse and the start of display data.
#      HT = FP + HDP + BP  and VT = VFP + VDP + VBP (sometimes plus sync pulse width)
# Unfortunately, the controller does not use these front/back porch times, instead it uses an starting time
# in the front porch area and defines (see also figures in chapter 13.3 of the SSD1963 data sheet)
# HPS  Time from that horiz. starting point to the start of the horzontal display area
# LPS  Time from that horiz. starting point to the horizontal sync pulse
# VPS  Time from the vert. starting point to the first line
# FPS  Time from the vert. starting point to the vertical sync pulse
#
# So the following relations must be held:
#
# HT >  HDP + HPS
# HPS >= HPW + LPS 
# HPS = Back Porch - LPS, or HPS = Horizontal back Porch
# VT > VDP + VPS
# VPS >= VPW + FPS
# VPS = Back Porch - FPS, or VPS = Vertical back Porch
#
# LPS or FPS may have a value of zero, since the length of the front porch is detemined by the 
# other figures
#
# The best is to start with the recomendations of the lCD data sheet for Back porch, grab a
# sync pulse with and the determine the other, such that they meet the relations. Typically, these
# values allow for some ambuigity. 
# 
            if lcd_type == "LB04301":  # Size 480x272, 4.3", 24 Bit, 4.3"
                #
                # Value            Min    Typical   Max
                # DotClock        5 MHZ    9 MHz    12 MHz
                # HT (Hor. Total   490     531      612
                # HDP (Hor. Disp)          480
                # HBP (back porch)  8      43
                # HFP (Fr. porch)   2       8
                # HPW (Hor. sync)   1
                # VT (Vert. Total) 275     288      335
                # VDP (Vert. Disp)         272
                # VBP (back porch)  2       12
                # VFP (fr. porch)   1       4
                # VPW (vert. sync)  1       10
                #
                # This table in combination with the relation above leads to the settings:
                # HPS = 43, HPW = 8, LPS = 0, HT = 531
                # VPS = 14, VPW = 10, FPS = 0, VT = 288
                #
                self.disp_x_size = 479
                self.disp_y_size = 271
                self.tft_cmd_data_AS(0xe6, bytearray(b'\x01\x70\xa3'), 3) # PLL setting for PCLK
                    # (9MHz * 1048576 / 100MHz) - 1 = 94371 = 0x170a3
                self.tft_cmd_data_AS(0xb0, bytearray(  # # LCD SPECIFICATION
                    [0x20,                # 24 Color bits, HSync/VSync low, No Dithering
                     0x00,                # TFT mode
                     self.disp_x_size >> 8, self.disp_x_size & 0xff, # physical Width of TFT
                     self.disp_y_size >> 8, self.disp_y_size & 0xff, # physical Height of TFT
                     0x00]), 7)  # Last byte only required for a serial TFT
                self.tft_cmd_data_AS(0xb4, bytearray(b'\x02\x13\x00\x2b\x08\x00\x00\x00'), 8) 
                        # HSYNC,  Set HT 531  HPS 43   HPW=Sync pulse 8 LPS 0
                self.tft_cmd_data_AS(0xb6, bytearray(b'\x01\x20\x00\x0e\x0a\x00\x00'), 7) 
                        # VSYNC,  Set VT 288  VPS 14 VPW 10 FPS 0
                self.tft_cmd_data_AS(0x36, bytearray([(h_flip & 1) << 1 | (v_flip) & 1]), 1) 
                        # rotation/ flip, etc., t.b.d. 
            elif lcd_type == "AT070TN92": # Size 800x480, 7", 18 Bit, lower color bits ignored
                #
                # Value            Min     Typical   Max
                # DotClock       26.4 MHz 33.3 MHz  46.8 MHz
                # HT (Hor. Total   862     1056     1200
                # HDP (Hor. Disp)          800
                # HBP (back porch)  46      46       46
                # HFP (Fr. porch)   16     210      254
                # HPW (Hor. sync)   1                40
                # VT (Vert. Total) 510     525      650
                # VDP (Vert. Disp)         480
                # VBP (back porch)  23      23       23
                # VFP (fr. porch)   7       22      147
                # VPW (vert. sync)  1                20
                #
                # This table in combination with the relation above leads to the settings:
                # HPS = 46, HPW = 8,  LPS = 0, HT = 1056
                # VPS = 23, VPW = 10, VPS = 0, VT = 525
                #
                self.disp_x_size = 799
                self.disp_y_size = 479
                self.tft_cmd_data_AS(0xe6, bytearray(b'\x05\x53\xf6'), 3) # PLL setting for PCLK
                    # (33.3MHz * 1048576 / 100MHz) - 1 = 349174 = 0x553f6
                self.tft_cmd_data_AS(0xb0, bytearray(  # # LCD SPECIFICATION
                    [0x00,                # 18 Color bits, HSync/VSync low, No Dithering/FRC
                     0x00,                # TFT mode
                     self.disp_x_size >> 8, self.disp_x_size & 0xff, # physical Width of TFT
                     self.disp_y_size >> 8, self.disp_y_size & 0xff, # physical Height of TFT
                     0x00]), 7)  # Last byte only required for a serial TFT
                self.tft_cmd_data_AS(0xb4, bytearray(b'\x04\x1f\x00\x2e\x08\x00\x00\x00'), 8) 
                        # HSYNC,      Set HT 1056  HPS 46  HPW 8 LPS 0
                self.tft_cmd_data_AS(0xb6, bytearray(b'\x02\x0c\x00\x17\x08\x00\x00'), 7) 
                        # VSYNC,   Set VT 525  VPS 23 VPW 08 FPS 0
                self.tft_cmd_data_AS(0x36, bytearray([(h_flip & 1) << 1 | (v_flip) & 1]), 1) 
                        # rotation/ flip, etc., t.b.d. 
            else:
                print("Wrong Parameter lcd_type: ", lcd_type)
                return
            self.tft_cmd_data_AS(0xBA, bytearray(b'\x0f'), 1) # GPIO[3:0] out 1
            self.tft_cmd_data_AS(0xB8, bytearray(b'\x07\x01'), 1) # GPIO3=input, GPIO[2:0]=output

            self.tft_cmd_data_AS(0xf0, bytearray(b'\x00'), 1) # Pixel data Interface 8 Bit

            self.tft_cmd(0x29)             # Display on
            self.tft_cmd_data_AS(0xbe, bytearray(b'\x06\xf0\x01\xf0\x00\x00'), 6) 
                    # Set PWM for B/L
            self.tft_cmd_data_AS(0xd0, bytearray(b'\x0d'), 1) # Set DBC: enable, agressive
        else:
            print("Wrong Parameter controller: ", controller)
            return
#
# Init done. clear Screen and switch BG LED on
#
        self.clrSCR()           # clear the display
        self.pin_led.value(1)  ## switch BG LED on
#
# Return screen dimensions
#
    def getScreensize(self):
        if self.orientation == LANDSCAPE:
            return (self.disp_x_size + 1, self.disp_y_size + 1)
        else:
            return (self.disp_y_size + 1, self.disp_x_size + 1)
#
# set the color used for the draw commands
#            
    def setColor(self, red, green, blue):
        self.color = [red, green, blue]
        self.colorvect = bytearray(self.color)  # prepare byte array
#
# set BG color used for 
# 
    def setBGColor(self, red, green, blue):
        self.BGcolor = [red, green, blue]
        self.BGcolorvect = bytearray(self.BGcolor)  # prepare byte array
#
# Draw a single pixel at location x, y
# Rather slow at 40µs/Pixel
#        
    def drawPixel(self, x, y):
        self.setXY(x, y, x, y)
        self.displaySCR_AS(self.colorvect, 1)  # 
#
# clear screen, set it to BG color.
#             
    def clrSCR(self):
        self.clrXY()
        self.fillSCR_AS(self.BGcolorvect, (self.disp_x_size + 1) * (self.disp_y_size + 1))
#
# Draw a line from x1, y1 to x2, y2 with the color set by setColor()
# Straight port from the UTFT Library at Rinky-Dink Electronics
# 
    def drawLine(self, x1, y1, x2, y2): 
        if y1 == y2:
            self.drawHLine(x1, y1, x2 - x1)
        elif x1 == x2:
            self.drawVLine(x1, y2, y2 - y1)
        else:
            dx, xstep  = (x2 - x1, 1) if x2 > x1 else (x1 - x2, -1)
            dy, ystep  = (y2 - y1, 1) if y2 > y1 else (y1 - y2, -1)
            col, row = x1, y1
            if dx < dy:
                t = - (dy >> 1)
                while True:
                    self.drawPixel(col, row)
                    if row == y2:
                        return
                    row += ystep
                    t += dx
                    if t >= 0:
                        col += xstep
                        t -= dy
            else:
                t = - (dx >> 1)
                while True:
                    self.drawPixel(col, row)
                    if col == x2:
                        return
                    col += xstep
                    t += dy
                    if t >= 0:
                        row += ystep
                        t -= dx
#
# Draw a horizontal line with 1 Pixel width, from x,y to x+l, y
# Straight port from the UTFT Library at Rinky-Dink Electronics
# 
    def drawHLine(self, x, y, l): # draw horiontal Line
        if l < 0:  # negative length, swap parameters
            l = -l
            x -= l
        self.setXY(x, y, x + l, y) # set display window
        self.fillSCR_AS(self.colorvect, l)
#
# Draw a vertical line with 1 Pixel width, from x,y to x, y + 1
# Straight port from the UTFT Library at Rinky-Dink Electronics
# 
    def drawVLine(self, x, y, l): # draw horiontal Line
        if l < 0:  # negative length, swap parameters
            l = -l
            y -= l
        self.setXY(x, y, x, y + l) # set display window
        self.fillSCR_AS(self.colorvect, l)
#
# Draw rectangle from x1, y1, to x2, y2
# Straight port from the UTFT Library at Rinky-Dink Electronics
#
    def drawRectangle(self, x1, y1, x2, y2):
        if x1 > x2:
            t = x1; x1 = x2; x2 = t
        if y1 > y2:
            t = y1; y1 = y2; y2 = t
    	self.drawHLine(x1, y1, x2-x1)
        self.drawHLine(x1, y2, x2-x1)
        self.drawVLine(x1, y1, y2-y1)
        self.drawVLine(x2, y1, y2-y1)
#
# Fill rectangle
# Straight port from the UTFT Library at Rinky-Dink Electronics
#
    def fillRectangle(self, x1, y1, x2, y2):
        if x1 > x2:
            t = x1; x1 = x2; x2 = t
        if y1 > y2:
            t = y1; y1 = y2; y2 = t
        self.setXY(x1, y1, x2, y2) # set display window
        self.fillSCR_AS(self.colorvect, (x2 - x1 + 1) * (y2 - y1 + 1))

#
# Draw smooth rectangle from x1, y1, to x2, y2
# Straight port from the UTFT Library at Rinky-Dink Electronics
#
    def drawClippedRectangle(self, x1, y1, x2, y2):
        if x1 > x2:
            t = x1; x1 = x2; x2 = t
        if y1 > y2:
            t = y1; y1 = y2; y2 = t
        if (x2-x1) > 4 and (y2-y1) > 4:
            self.drawPixel(x1 + 2,y1 + 1)
            self.drawPixel(x1 + 1,y1 + 2)
            self.drawPixel(x2 - 2,y1 + 1)
            self.drawPixel(x2 - 1,y1 + 2)
            self.drawPixel(x1 + 2,y2 - 1)
            self.drawPixel(x1 + 1,y2 - 2)
            self.drawPixel(x2 - 2,y2 - 1)
            self.drawPixel(x2 - 1,y2 - 2)
            self.drawHLine(x1 + 3, y1, x2 - x1 - 6)
            self.drawHLine(x1 + 3, y2, x2 - x1 - 6)
            self.drawVLine(x1, y1 + 3, y2 - y1 - 6)
            self.drawVLine(x2, y1 + 3, y2 - y1 - 6)
#
# Fill smooth rectangle from x1, y1, to x2, y2
# Straight port from the UTFT Library at Rinky-Dink Electronics
#
    def fillClippedRectangle(self, x1, y1, x2, y2):
        if x1 > x2:
            t = x1; x1 = x2; x2 = t
        if y1 > y2:
            t = y1; y1 = y2; y2 = t
        if (x2-x1) > 4 and (y2-y1) > 4:
            for i in range(((y2 - y1) // 2) + 1):
                if i == 0:
                    self.drawHLine(x1 + 3, y1 + i, x2 - x1 - 6)
                    self.drawHLine(x1 + 3, y2 - i, x2 - x1 - 6)
                elif i == 1:
                    self.drawHLine(x1 + 2, y1 + i, x2 - x1 - 4)
                    self.drawHLine(x1 + 2, y2 - i, x2 - x1 - 4)
                elif i == 2:
                    self.drawHLine(x1 + 1, y1 + i, x2 - x1 - 2)
                    self.drawHLine(x1 + 1, y2 - i, x2 - x1 - 2)
                else:
                    self.drawHLine(x1, y1 + i, x2 - x1)
                    self.drawHLine(x1, y2 - i, x2 - x1)
#
# draw a circle at x, y with radius
# Straight port from the UTFT Library at Rinky-Dink Electronics
#
    def drawCircle(self, x, y, radius):
    
        f = 1 - radius
        ddF_x = 1
        ddF_y = -2 * radius
        x1 = 0
        y1 = radius

        self.drawPixel(x, y + radius)
        self.drawPixel(x, y - radius)
        self.drawPixel(x + radius, y)
        self.drawPixel(x - radius, y)

        while x1 < y1:
            if f >= 0:
	            y1 -= 1
	            ddF_y += 2
	            f += ddF_y
            x1 += 1
            ddF_x += 2
            f += ddF_x
            self.drawPixel(x + x1, y + y1)
            self.drawPixel(x - x1, y + y1)
            self.drawPixel(x + x1, y - y1)
            self.drawPixel(x - x1, y - y1)
            self.drawPixel(x + y1, y + x1)
            self.drawPixel(x - y1, y + x1)
            self.drawPixel(x + y1, y - x1)
            self.drawPixel(x - y1, y - x1)
#
# fill a circle at x, y with radius
# Straight port from the UTFT Library at Rinky-Dink Electronics
#
    def fillCircle(self, x, y, radius):
    
        for y1 in range (-radius, 1): 
            for x1 in range (-radius, 1):
                if x1*x1+y1*y1 <= radius*radius: 
                    self.drawHLine(x + x1, y + y1, 2 * (-x1))
                    self.drawHLine(x + x1, y - y1, 2 * (-x1))
                    break;
#
# Draw a bitmap at x,y with size sx, sy
# The data must contain 3 bytes/pixel red/green/blue
# Other versions with packed data for the various BMP formats will follow.
#
    def drawBitmap(self, x, y, sx, sy, data):
        self.setXY(x, y, x + sx - 1, y + sy - 1)
        self.displaySCR_AS(data, sx * sy)
#
# Draw a bitmap at x,y with size sx, sy
# The data must contain 2 packed bytes/pixel red/green/blue
#
    def drawBitmap_565(self, x, y, sx, sy, data):
        self.setXY(x, y, x + sx - 1, y + sy - 1)
        self.displaySCR565_AS(data, sx * sy)
        
#
# Print string s using the small font at location x, y
# Characters are 8 col x 12 row pixels sized
#
    def printString(self, x, y, s, font, fgcolor = None, bgcolor = None):
        size = len(s)
        if fgcolor:
            if bgcolor:
                colorvect = bytearray(fgcolor) + bytearry(bgcolor)
            else: 
                colorvect = bytearray(fgcolor) + self.BGcolorvect
        else:
            colorvect = self.colorvect + self.BGcolorvect   
# reading the font's header info = 4 bytes
        cols = font[0]
        bytes = (cols + 7) // 8   # number of bytes/col
        rows = font[1]            # Rows 
        offset = font[2]          # Code of the first chars
        no_of_chars = font[3]     # Number of chars in font set
        buf = bytearray(size * cols * 3)
        bitmap = bytearray(size * bytes)
        for row in range(rows):
            cp = 0
            for col in range(size):
                index = ((ord(s[col]) & 0x7f) - offset)
                if index < 0 or index >= no_of_chars: 
                    index = 0
                for i in range(bytes):
                    bitmap[cp + i] = font[(index * rows + row) * bytes + 4 + i]
                cp += bytes
            buf[0] = cols
            self.expandBitmap(buf, bitmap, size * bytes, colorvect)
            self.drawBitmap(x, y + row, size * cols, 1, buf)
#
# Print string helper function for expanding the bitmap
# 
    @staticmethod
    @micropython.viper        
    def expandBitmap(buf: ptr8, bitmap: ptr8, size: int, color: ptr8):
        bp = 0
        charcols = buf[0]
        cols = charcols
        for col in range(size):
            bits = bitmap[col]
            for i in range(8):
                if bits & 0x80:
                    buf[bp] = color[0]
                    buf[bp + 1] = color[1]
                    buf[bp + 2] = color[2]
                else:
                    buf[bp] = color[3]
                    buf[bp + 1] = color[4]
                    buf[bp + 2] = color[5]
                bits <<= 1
                bp += 3
                cols -= 1
                if cols == 0: # Bit cols per char used up, go to next byte
                    cols = charcols
                    break
#
# Set the address range for various draw copmmands and set the TFT for expecting data
#
    def setXY(self, x1, y1, x2, y2): ## set the adress range, using function calls
        if self.orientation == PORTRAIT:
# set column address
            self.setXY_sub(0x2b, x1, x2)
# set row address            
            self.setXY_sub(0x2a, y1, y2)
        else:
# set column address
            self.setXY_sub(0x2a, x1, x2)
# set row address            
            self.setXY_sub(0x2b, y1, y2)
# sub-function, saving some time
    @staticmethod
    @micropython.viper        
    def setXY_sub(cmd: int, x1: int, x2:int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        gpioa[0] = cmd         # command
        gpiob[1] = D_C | WR     # set C/D and WR low
        gpiob[0] = D_C | WR     # set C/D and WR high

        gpioa[0] = x1 >> 8  # high byte of x1
        gpiob[1] = WR       # set WR low. C/D still high
        gpiob[0] = WR       # set WR high again

        gpioa[0] = x1 & 0xff# low byte of x1
        gpiob[1] = WR       # set WR low. C/D still high
        gpiob[0] = WR       # set WR high again

        gpioa[0] = x2 >> 8  # high byte of x2
        gpiob[1] = WR       # set WR low. C/D still high
        gpiob[0] = WR       # set WR high again

        gpioa[0] = x2 & 0xff# low byte of x2
        gpiob[1] = WR       # set WR low. C/D still high
        gpiob[0] = WR       # set WR high again

        gpioa[0] = 0x2c         # Start data entry
        gpiob[1] = D_C | WR     # set C/D and WR low
        gpiob[0] = D_C | WR     # set C/D and WR high
#
# reset the address range to fullscreen
#       
    def clrXY(self):
        self.setXY(0, 0, self.disp_x_size, self.disp_y_size)
#
# Fill screen by writing size pixels with the color given in data
# data must be 3 bytes of red, green, blue
# The area to be filled has to be set in advance by setXY
# The speed is about 440 ns/pixel
#
    @staticmethod
    @micropython.viper        
    def fillSCR(data: ptr8, size: int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        while size:
            gpioa[0] = data[0]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again

            gpioa[0] = data[1]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again

            gpioa[0] = data[2]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again
            size -= 1
#
# Display screen by writing size pixels with the data
# data must contains size triplets of red, green and blue data values
# The area to be filled has to be set in advance by setXY
# The speed is about 650 ns/pixel
#
    @staticmethod
    @micropython.viper        
    def displaySCR(data: ptr8, size: int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        ptr = 0
        while size:
            gpioa[0] = data[ptr]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again

            gpioa[0] = data[ptr + 1]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again

            gpioa[0] = data[ptr + 2]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again
            ptr += 3
            size -= 1
#
# Display screen by writing size pixels with the data
# data must contains size packed words of red, green and blue data values
# The area to be filled has to be set in advance by setXY
# The speed is about 650 ns/pixel
#
    @staticmethod
    @micropython.viper        
    def displaySCR565(data: ptr8, size: int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        ptr = 0
        while size:
            gpioa[0] = data[ptr] & 0xf8  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again

            gpioa[0] = (data[ptr] << 5 | (data[ptr +1] >> 3) & 0xfc) # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again

            gpioa[0] = (data[ptr + 1] << 3) # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again
            ptr += 2
            size -= 1
#
# Assembler version of 
# Fill screen by writing size pixels with the color given in data
# data must be 3 bytes of red, green, blue
# The area to be filled has to be set in advance by setXY
# The speed is about 214 ns/pixel
#
    @staticmethod
    @micropython.asm_thumb
    def fillSCR_AS(r0, r1):  # r0: ptr to data, r1: number of pixels (3 bytes/pixel)
# set up pointers to GPIO
# r5: bit mask for control lines
# r6: GPIOA OODR register ptr
# r7: GPIOB BSSRL register ptr
        mov(r5, WR)
        movwt(r6, stm.GPIOA) # target
        add (r6, stm.GPIO_ODR)
        movwt(r7, stm.GPIOB)
        add (r7, stm.GPIO_BSRRL)
        ldrb(r2, [r0, 0])  # red   
        ldrb(r3, [r0, 1])  # green
        ldrb(r4, [r0, 2])  # blue
        b(loopend)

        label(loopstart)
        strb(r2, [r6, 0])  # Store red
        strb(r5, [r7, 2])  # WR low
#        nop()
        strb(r5, [r7, 0])  # WR high

        strb(r3, [r6, 0])  # store blue
        strb(r5, [r7, 2])  # WR low
        nop()
        strb(r5, [r7, 0])  # WR high
        
        strb(r4, [r6, 0])  # store blue
        strb(r5, [r7, 2])  # WR low
#        nop()
        strb(r5, [r7, 0])  # WR high

        label(loopend)
        sub (r1, 1)  # End of loop?
        bpl(loopstart)
#
# Assembler version of:
# Fill screen by writing size pixels with the data
# data must contains size triplets of red, green and blue data values
# The area to be filled has to be set in advance by setXY
# the speed is 266 ns for a byte triple 
#
    @staticmethod
    @micropython.asm_thumb
    def displaySCR_AS(r0, r1):  # r0: ptr to data, r1: is number of pixels (3 bytes/pixel)
# set up pointers to GPIO
# r5: bit mask for control lines
# r6: GPIOA OODR register ptr
# r7: GPIOB BSSRL register ptr
        mov(r5, WR)
        movwt(r6, stm.GPIOA) # target
        add (r6, stm.GPIO_ODR)
        movwt(r7, stm.GPIOB)
        add (r7, stm.GPIO_BSRRL)
        b(loopend)

        label(loopstart)
        ldrb(r2, [r0, 0])  # red   
        strb(r2, [r6, 0])  # Store red
        strb(r5, [r7, 2])  # WR low
        strb(r5, [r7, 0])  # WR high

        ldrb(r2, [r0, 1])  # pre green
        strb(r2, [r6, 0])  # store greem
        strb(r5, [r7, 2])  # WR low
        strb(r5, [r7, 0])  # WR high
        
        ldrb(r2, [r0, 2])  # blue
        strb(r2, [r6, 0])  # store blue
        strb(r5, [r7, 2])  # WR low
        strb(r5, [r7, 0])  # WR high

        add (r0, 3)  # advance data ptr

        label(loopend)
        sub (r1, 1)  # End of loop?
        bpl(loopstart)
# Assembler version of:
# Fill screen by writing size pixels with the data
# data must contains size packed duplets of red, green and blue data values
# The area to be filled has to be set in advance by setXY
# the speed is 266 ns for a byte pixel 
#
    @staticmethod
    @micropython.asm_thumb
    def displaySCR565_AS(r0, r1):  # r0: ptr to data, r1: is number of pixels (3 bytes/pixel)
# set up pointers to GPIO
# r5: bit mask for control lines
# r6: GPIOA OODR register ptr
# r7: GPIOB BSSRL register ptr
        mov(r5, WR)
        movwt(r6, stm.GPIOA) # target
        add (r6, stm.GPIO_ODR)
        movwt(r7, stm.GPIOB)
        add (r7, stm.GPIO_BSRRL)
        b(loopend)

        label(loopstart)

        ldrb(r2, [r0, 0])  # red   
        mov (r3, 0xf8)     # mask out lower 3 bits
        and_(r2, r3)        
        strb(r2, [r6, 0])  # Store red
        strb(r5, [r7, 2])  # WR low
        strb(r5, [r7, 0])  # WR high

        ldrb(r2, [r0, 0])  # pre green
        mov (r3, 5)        # shift 5 bits up to 
        lsl(r2, r3)
        ldrb(r4, [r0, 1])  # get the next 3 bits
        mov (r3, 3)        # shift 3 to the right
        lsr(r4, r3)
        orr(r2, r4)        # add them to the first bits
        mov(r3, 0xfc)      # mask off the lower two bits
        and_(r2, r3)
        strb(r2, [r6, 0])  # store green
        strb(r5, [r7, 2])  # WR low
        strb(r5, [r7, 0])  # WR high
        
        ldrb(r2, [r0, 1])  # blue
        mov (r3, 3)
        lsl(r2, r3)
        strb(r2, [r6, 0])  # store blue
        strb(r5, [r7, 2])  # WR low
        strb(r5, [r7, 0])  # WR high
        
        add (r0, 2)  # advance data ptr

        label(loopend)

        sub (r1, 1)  # End of loop?
        bpl(loopstart)
#
# Send a command and data to the TFT controller
# cmd is the command byte, data must be a bytearray object with the command payload,
# int is the size of the data
# For the startup-phase use this function.
#
    @staticmethod
    @micropython.viper        
    def tft_cmd_data(cmd: int, data: ptr8, size: int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        gpioa[0] = cmd          # set data on port A
        gpiob[1] = D_C | WR     # set C/D and WR low
        gpiob[0] = D_C | WR     # set C/D and WR high
        for i in range(size):
            gpioa[0] = data[i]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again
#
# Assembler version of send command & data to the TFT controller
# data must be a bytearray object, int is the size of the data.
# The speed is about 120 ns/byte
#
    @staticmethod
    @micropython.asm_thumb
    def tft_cmd_data_AS(r0, r1, r2):  # r0: command, r1: ptr to data, r2 is size in bytes
# set up pointers to GPIO
# r5: bit mask for control lines
# r6: GPIOA OODR register ptr
# r7: GPIOB BSSRL register ptr
        movwt(r6, stm.GPIOA) # target
        add (r6, stm.GPIO_ODR)
        movwt(r7, stm.GPIOB)
        add (r7, stm.GPIO_BSRRL)
# Emit command byte
        mov(r5, WR | D_C)
        strb(r0, [r6, 0])  # set command byte
        strh(r5, [r7, 2])  # WR and D_C low
        strh(r5, [r7, 0])  # WR and D_C high
# now loop though data
        mov(r5, WR)
        b(loopend)

        label(loopstart)
        ldrb(r4, [r1, 0])  # load data   
        strb(r4, [r6, 0])  # Store data
        strh(r5, [r7, 2])  # WR low
        strh(r5, [r7, 0])  # WR high
        add (r1, 1)  # advance data ptr

        label(loopend)
        sub (r2, 1)  # End of loop?
        bpl(loopstart)
#
# Send a command to the TFT controller
#
    @staticmethod
    @micropython.viper        
    def tft_cmd(cmd: int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        gpioa[0] = cmd          # set data on port A
        gpiob[1] = D_C | WR     # set C/D and WR low
        gpiob[0] = D_C | WR     # set C/D and WR high
#
# Send data to the TFT controller
# data must be a bytearray object, int is the size of the data.
# the speed is about 460 ns/byte
#
    @staticmethod
    @micropython.viper        
    def tft_data(data: ptr8, size: int):
        gpioa = ptr8(stm.GPIOA + stm.GPIO_ODR)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        for i in range(size):
            gpioa[0] = data[i]  # set data on port A
            gpiob[1] = WR       # set WR low. C/D still high
            gpiob[0] = WR       # set WR high again
#
# Assembler version of send data to the TFT controller
# data must be a bytearray object, int is the size of the data.
# The speed is about 120 ns/byte
#
    @staticmethod
    @micropython.asm_thumb
    def tft_data_AS(r0, r1):  # r0: ptr to data, r1: is size in Bytes
# set up pointers to GPIO
# r5: bit mask for control lines
# r6: GPIOA OODR register ptr
# r7: GPIOB BSSRL register ptr
        movwt(r6, stm.GPIOA) # target
        add (r6, stm.GPIO_ODR)
        movwt(r7, stm.GPIOB)
        add (r7, stm.GPIO_BSRRL)
        mov(r5, WR)
# and go, first test size for 0
        b(loopend)
 
        label(loopstart)
        ldrb(r3, [r0, 0])  # load data   
        strb(r3, [r6, 0])  # Store data
        strh(r5, [r7, 2])  # WR low
        strh(r5, [r7, 0])  # WR high
       
        add (r0, 1)  # advance data ptr
        label(loopend)
        sub (r1, 1)  # End of loop?
        bpl(loopstart)
#
# Read data from the TFT controller
# cmd is the command byte, data must be a bytearray object for the returned data,
# int is the expected size of the data. data must match at least that size
#
    @staticmethod
    @micropython.viper        
    def tft_read_data(cmd: int, data: ptr8, size: int):
        gpioa = ptr8(stm.GPIOA)
        gpioam = ptr16(stm.GPIOA + stm.GPIO_MODER)
        gpiob = ptr16(stm.GPIOB + stm.GPIO_BSRRL)
        gpioa[stm.GPIO_ODR] = cmd  # set data on port A
        gpiob[1] = D_C | WR     # set C/D and WR low
        gpiob[0] = D_C | WR     # set C/D and WR high
        gpioam[0] = 0  # Configure X1..X8 as Input
        for i in range(size):
            gpiob[1] = RD       # set RD low. C/D still high
            gpiob[0] = RD       # set RD high again
            data[i] = gpioa[stm.GPIO_IDR]  # get data from port A
        gpioam[0] = 0x5555  # configure X1..X8 as Output

#
# Some sample code
#
import os
def displayfile(mytft, name, mode, width, height):
    with open(name, "rb") as f:
        if mode == 565:
            b = bytearray(width * 2)
            for row in range(height):
                n = f.readinto(b)
                if not n:
                    break
                mytft.drawBitmap_565(0, row, width, 1, b)
        else:
            b = bytearray(width * 3)
            for row in range(height):
                n = f.readinto(b)
                if not n:
                    break
                mytft.drawBitmap(0, row, width, 1, b)
        mytft.setColor(0, 0, 0)
        mytft.fillRectangle(0, row, width, height)
        mytft.setColor(255, 255, 255)

def main(v_flip = False, h_flip = False):

    mytft = TFT("SSD1963", "LB04301", LANDSCAPE, v_flip, h_flip)
    width, height = mytft.getScreensize()
    mytft.printString(10, 20, "0123456789" * 5, SmallFont, (255,0,0))
    mytft.printString(10, 40, "0123456789" * 5, SmallFont, (255,0,0))
    pyb.delay(2000)
    mytft.printString(10, 20, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", BigFont, (0, 255, 0))
    mytft.printString(10, 60, "abcdefghijklmnopqrstuvwxyz", BigFont, (0, 255, 0))
    mytft.printString(10, 100, "0123456789!\"§$%&/()=?", BigFont, (0, 255, 0))
    pyb.delay(2000)
    mytft.setColor(255,255,255)
    mytft.drawClippedRectangle(0, 150, 100, 250)
    mytft.fillClippedRectangle(200, 150, 300, 250)
    pyb.delay(2000)
    mytft.clrSCR()
    cnt = 10
    while cnt >= 0:
        mytft.printString((width // 2) - 32, (height // 2) - 30, "{:2}".format(cnt), SevenSegNumFont)
        cnt -= 1
        pyb.delay(1000)
    
    mytft.clrSCR()
    buf = bytearray(5000)
    with open ("logo50.raw", "rb") as f:
        n = f.readinto(buf)
    
    for i in range(10):
        mytft.clrSCR()
        for cnt in range(50):
            x = pyb.rng() % (width - 51)
            y = pyb.rng() % (height - 51)
            mytft.drawBitmap_565(x, y, 50, 50, buf)
        pyb.delay(1000)
    while True:
        displayfile(mytft, "F0010.raw", 565, width, height)
        pyb.delay(6000)
        displayfile(mytft, "F0011.raw", 565, width, height)
        pyb.delay(6000)
        displayfile(mytft, "F0013.data", 24, width, height)
        pyb.delay(6000)
                

