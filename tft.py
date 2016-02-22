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
    
    def __init__(self, model = "SSD1963", width = 480, height = 272):
        self.tft_init(model, width, height)
    
    def tft_init(self, model = "SSD1963", width = 480, height = 272):
#
# For convenience, define X1..X1 and Y9..Y12 as output port using thy python functions.
# X1..X8 will be redefind on the fly as Input by accessing the MODER control registers 
# when needed. Y9 is treate seperately, since it is used for Reset, which is done at python level
# since it need long delays anyhow, 5 and 15 ms vs. 10 µs.
#
        self.model = model
        self.disp_x_size = width - 1
        self.disp_y_size = height - 1
        if width < height:
            self.mode = PORTRAIT
        else:
            self.mode = LANDSCAPE
        
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
# This is preliminary for the SSD1963 controller and a specific size. Generalization follows.
# data taken from the UTFT lib & SSD1963 data sheet
#
        if self.model == "SSD1963":           # 1st approach for 480 x 272
            self.tft_cmd_data(0xe2, bytearray(b'\x23\x02\x54'), 3) # PLL multiplier, set PLL clock to 120M
                                                     # N=0x37 for 6.5M, 0x23 for 10M crystal 
            self.tft_cmd_data(0xe0, bytearray(b'\x01'), 1) # PLL Enable
            pyb.delay(10)
            self.tft_cmd_data(0xe0, bytearray(b'\x03'), 1)
            pyb.delay(10)
            self.tft_cmd(0x01)                     # software reset
            pyb.delay(10)
            self.tft_cmd_data_AS(0xe6, bytearray(b'\x01\x1f\xff'), 3) # PLL setting for PCLK, depends on resolution
            self.tft_cmd_data_AS(0xb0, bytearray(b'\x20\x00\x01\xdf\x01\x0f\x00'), 7) 
                    # LCD SPECIFICATION, 479 x 271 =  1df x 10f
            self.tft_cmd_data_AS(0xb4, bytearray(b'\x02\x13\x00\x08\x2b\x00\x02\x00'), 8) 
                    # HSYNC,               Set HT 531  HPS 08  HPW 43 LPS 2
            self.tft_cmd_data_AS(0xb6, bytearray(b'\x01\x20\x00\x04\x0c\x00\x02'), 7) 
                    # VSYNC,               Set VT 288  VPS 04 VPW 12 FPS 2
            self.tft_cmd_data_AS(0xBA, bytearray(b'\x0f'), 1) # GPIO[3:0] out 1
            self.tft_cmd_data_AS(0xB8, bytearray(b'\x07\x01'), 1) # GPIO3=input, GPIO[2:0]=output
            if self.mode == PORTRAIT:
                self.tft_cmd_data_AS(0x36, bytearray(b'\x01'), 1) # rotation/Mirro, etc., t.b.t. 
            else:
                self.tft_cmd_data_AS(0x36, bytearray(b'\x00'), 1) # rotation/Mirro, etc. t.b.t.
            self.tft_cmd_data_AS(0xf0, bytearray(b'\x00'), 1) # Pixel data Interface 8 Bit

            self.tft_cmd(0x29)             # Display on
            self.tft_cmd_data_AS(0xbe, bytearray(b'\x06\xf0\x01\xf0\x00\x00'), 6) 
                    # Set PWM for B/L
            self.tft_cmd_data_AS(0xd0, bytearray(b'\x0d'), 1) # Set DBC: enable, agressive
        else:
            return
#
# Init done. clear Screen and switch BG LED on
#
        self.clrSCR()           # clear the display
        self.pin_led.value(1)  ## switch BG LED on
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
    @micropython.native
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
        self.fillSCR(self.colorvect, l)
#
# Draw a vertical line with 1 Pixel width, from x,y to x, y + 1
# Straight port from the UTFT Library at Rinky-Dink Electronics
# 
    def drawVLine(self, x, y, l): # draw horiontal Line
        if l < 0:  # negative length, swap parameters
            l = -l
            y -= l
        self.setXY(x, y, x, y + l) # set display window
        self.fillSCR(self.colorvect, l)
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
    def printString(self, x, y, s, font = None, fgcolor = None, bgcolor = None):
        size = len(s)
        if fgcolor:
            if bgcolor:
                colorvect = bytearray(fgcolor) + bytearry(bgcolor)
            else: 
                colorvect = bytearray(fgcolor) + self.BGcolorvect
        else:
            colorvect = self.colorvect + self.BGcolorvect       
        if font == None:
            font = SmallFont
        cols = font[0] // 8
        rows = font[1]
        offset = font[2]
        no_of_chars = font[3]
        buf = bytearray(' ' * (size * 24 * cols))
        bitmap = bytearray(' ' * (size * cols))
        for row in range(rows):
            cp = 0
            for col in range(size):
                index = ((ord(s[col]) & 0x7f) - offset)
                if index < 0 or index >= no_of_chars: 
                    index = 0
                for i in range(cols):
                    bitmap[cp + i] = font[(index * rows + row) * cols + 4 + i]
                cp += cols
            self.expandBitmap(buf, bitmap, size * cols, colorvect)
            self.drawBitmap(x, y + row, size * cols * 8, 1, buf)
#
# Print string helper function for expanding the bitmap
# 
    @staticmethod
    @micropython.viper        
    def expandBitmap(buf: ptr8, bitmap: ptr8, size: int, color: ptr8):
        bp = 0
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
#
# Set the addres range for various draw copmmands and set the TFT for expecting data
#
    def setXY(self, x1, y1, x2, y2): ## set the adress range, using function calls
        if self.mode == PORTRAIT:
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

            gpioa[0] = data[ptr + 1] << 3 # set data on port A
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
def main():
    mytft = TFT("SSD1963", 480, 272)

    b = bytearray([0 for i in range(480 * 2)])

    cnt = 12
    while cnt >= 0:
        mytft.printString(10, 20, "{:2}".format(cnt), SevenSegNumFont)
        cnt -= 1
        pyb.delay(1000)
    
    mytft.setColor(255, 255, 0)
    mytft.setBGColor(0, 0, 0)
    start = pyb.millis()
    mytft.drawCircle(100, 100, 90)
    time = pyb.elapsed_millis(start)
    print("time = ", time)
    pyb.delay(1000)
    start = pyb.millis()
    mytft.fillCircle(300, 150, 90)
    time = pyb.elapsed_millis(start)
    print("time = ", time)
    
    while True:
        val = input("next :")
        if val == "q": break
        mytft.clrSCR()

        start = pyb.millis()
        with open("F0010.raw", "rb") as f:
            for row in range(272):
                n = f.readinto(b)
                if not n:
                    break
                mytft.drawBitmap_565(0, row, 480, 1, b)
        time = pyb.elapsed_millis(start)
        print("time = ", time)
    mytft.clrSCR()
