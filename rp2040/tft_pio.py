#
# The MIT License (MIT)
#
# Copyright (c) 2016 Robert Hammelrath
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Low level I/O drivers for the class supporting TFT LC-displays
# with a parallel Interface
# First example: Controller SSD1963
# It uses X1..X8 for data and Y3, Y9, Y10, Y11 and Y12 for control signals.
# The minimal connection is:
# X1..X8 for data, Y9 for /Reset, Y10 for /RD, Y11 for /WR and Y12 for /RS
# Then LED must be hard tied to Vcc and /CS to GND.
#



import rp2
from machine import Pin, freq, idle
import array
import time

# define constants
#
RESET  = const(14)  ## Pin 14
D_C    = const(10) ## Pin 10
RD     = const(11)  ## Pin 11
WR     = const(12)  ## Pin 12
BASEPIN = const(2)  ## Pin 2

## CS is not used and must be hard tied to GND

PORTRAIT = const(1)
LANDSCAPE = const(0)

DMA_BASE = const(0x50000000)
READ_ADDR = const(0)
WRITE_ADDR = const(1)
TRANS_COUNT = const(2)
CTRL_TRIG = const(3)
CTRL_ALIAS = const(4)
TRANS_COUNT_ALIAS = const(9)
CHAN_ABORT = const(0x111)  # Address offset / 4
BUSY = const(1 << 24)

PIO0_BASE = const(0x50200000)
PIO0_BASE_TXF0 = const(PIO0_BASE+0x10)
PIO0_BASE_TXF1 = const(PIO0_BASE+0x14)
PIO0_BASE_TXF2 = const(PIO0_BASE+0x18)
PIO0_BASE_TXF3 = const(PIO0_BASE+0x1c)
PIO0_BASE_RXF0 = const(PIO0_BASE+0x20)
PIO0_BASE_RXF1 = const(PIO0_BASE+0x24)
PIO0_BASE_RXF2 = const(PIO0_BASE+0x28)
PIO0_BASE_RXF3 = const(PIO0_BASE+0x2c)
PIO0_INSTR_MEM = const(PIO0_BASE+0x48)

    # create the required PIO object
class TFT_IO:
    def __init__(self, base_pin=BASEPIN, orientation=LANDSCAPE, reset_pin=RESET):

        self.pin_reset = Pin(reset_pin, Pin.OUT, value=1)
# Reset the device
        time.sleep_ms(10)
        self.pin_reset.value(0)  ## Low
        time.sleep_ms(20)
        self.pin_reset.value(1)  ## set high again
        time.sleep_ms(20)
# create the array for the Cursor settings and pre-set the commands
        self.ar_setxy = array.array("H", bytearray(22))
        if orientation == LANDSCAPE:
            self.ar_setxy[0] = 0x2a
            self.ar_setxy[5] = 0x2b
        else:
            self.ar_setxy[0] = 0x2b
            self.ar_setxy[5] = 0x2a
        self.ar_setxy[10] = 0x2c

# create the array for the drawPixel and pre-set the commands
        self.ar_drawPixel = array.array("H", bytearray(28))
        self.ar_drawPixel[0:11] = self.ar_setxy

# set frequencies and mwait time factors
        self.tx_freq = 25_000_000
        self.rx_freq = 25_000_000
        self.tx_limit = max((20_000 * 480 * 800 * 3) // self.rx_freq, 1)
        self.rx_limit = max((30_000 * 100 * 100 * 3) // self.rx_freq, 1)
        TFT_IO.DMA_chan_abort(0)  # cancel any actions

# create the state machines

        self.sm_data_write_triple = rp2.StateMachine(0, TFT_IO.pio_data_write_triple, freq=self.tx_freq,
                            sideset_base=Pin(base_pin + 8), out_base=Pin(base_pin))

        self.sm_data_write_byte = rp2.StateMachine(1, TFT_IO.pio_data_write_byte, freq=self.tx_freq,
                            sideset_base=Pin(base_pin + 8), out_base=Pin(base_pin))

        self.sm_cmd_write = rp2.StateMachine(2, TFT_IO.pio_cmd_write, freq=self.tx_freq,
                            sideset_base=Pin(base_pin + 9), out_base=Pin(base_pin))

        self.sm_cmd_data_read = rp2.StateMachine(3, TFT_IO.pio_cmd_data_read,
                            freq=self.rx_freq,
                            sideset_base=Pin(base_pin + 8), out_base=Pin(base_pin),
                            in_base=Pin(base_pin))

# Set up the DMA control patterns
        IRQ_QUIET = const(0x1) # do not generate an interrupt
        CHAIN_TO = const(0) # do not chain
        RING_SEL = const(0)
        RING_SIZE = const(0) # no wrapping
        HIGH_PRIORITY = const(1)
        EN = const(1)

        TREQ_SEL = (0x00) # wait for PIO0_TX0
        INCR_WRITE = (0) # for write to array
        INCR_READ = (0) # for read from array
        DATA_SIZE = (2) # 32-bit word transfer
        self.DMA_fill_control = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                            (RING_SIZE << 6) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                            (HIGH_PRIORITY << 1) | (EN << 0))

        TREQ_SEL = (0x01) # wait for PIO0_TX1
        INCR_WRITE = (0) # for write to array
        INCR_READ = (1) # for read from array
        DATA_SIZE = (0) # 8-bit word transfer
        self.DMA_data_write_control = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                            (RING_SIZE << 6) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                            (HIGH_PRIORITY << 1) | (EN << 0))

        TREQ_SEL = (0x07) # wait for PIO0_RX3
        INCR_WRITE = (1) # for write to array
        INCR_READ = (0) # for read from array
        DATA_SIZE = (0) # 8-bit word transfer
        self.DMA_data_read_control = ((IRQ_QUIET << 21) | (TREQ_SEL << 15) | (CHAIN_TO << 11) | (RING_SEL << 10) |
                            (RING_SIZE << 6) | (INCR_WRITE << 5) | (INCR_READ << 4) | (DATA_SIZE << 2) |
                            (HIGH_PRIORITY << 1) | (EN << 0))


# define the PIO codes
# writing command or data. D/C# is coded in the 9th bit
#
# fmt: off
    @staticmethod
    @rp2.asm_pio(
        sideset_init=(rp2.PIO.OUT_HIGH,) * 2,
        out_init=(rp2.PIO.OUT_HIGH,) * 9,
        out_shiftdir=rp2.PIO.SHIFT_RIGHT,
        autopull=True,
        pull_thresh=16)
    def pio_cmd_write():
        out(pins, 9)            .side(0b10)  # WR low, output 9 bit
        out(null, 7)            .side(0b11)  # WR high, discard 7 bit

# just write byte data bytes. Used with and w/o DMA
#
    @staticmethod
    @rp2.asm_pio(
        sideset_init=(rp2.PIO.OUT_HIGH,) * 3,
        out_init=(rp2.PIO.OUT_HIGH,) * 8,
        out_shiftdir=rp2.PIO.SHIFT_RIGHT,
        autopull=True,
        pull_thresh=8)
    def pio_data_write_byte():
        out(pins, 8)            .side(0b101)  # WR low, output data
        nop()                   .side(0b111)  # WR high

# just write data byte triples
# used for fill commands with DMA
    @staticmethod
    @rp2.asm_pio(
        sideset_init=(rp2.PIO.OUT_HIGH,) * 3,
        out_init=(rp2.PIO.OUT_HIGH,) * 8,
        out_shiftdir=rp2.PIO.SHIFT_RIGHT,
        autopull=True,
        pull_thresh=24)
    def pio_data_write_triple():
        out(pins, 8)            .side(0b101) # WR low, output data
        nop()                   .side(0b111) # WR high

# Write a command and read back data
# Switching the bus direction as needed
#
    @staticmethod
    @rp2.asm_pio(
        sideset_init=(rp2.PIO.OUT_HIGH,) * 3,
        out_init=(rp2.PIO.OUT_HIGH,) * 8,
        out_shiftdir=rp2.PIO.SHIFT_RIGHT,
        autopull=False,
        autopush=True,
        pull_thresh=16,
        push_thresh=8)
    def pio_cmd_data_read():
        pull()              .side(0b111)  # get number of bytes to read
        mov(x, osr)         .side(0b111)  # save it to the counter
        pull()              .side(0b100)  # WR low
        out(pins, 8)        .side(0b100)  # send the command
        nop()               .side(0b110)  # WR high
        out(pindirs, 8)     .side(0b011) [3] # and switch to input mode, RD Low
        nop()               .side(0b011) [3] # First read needs a delay, RD low

        label("again")
        nop()               .side(0b111)  # RD high
        in_(pins, 8)        .side(0b111)  # Get data
        jmp(x_dec, "again") .side(0b011)  # Loop, RD low

        pull()              .side(0b111)  # get the new pindir value
        out(pindirs, 8)     .side(0b111)  # and switch back to output mode

# fmt: on
#
# set up DMA0. Parameters:
# source address, destination address, # DMA tranfers, control word
#
    @staticmethod
    @micropython.viper
    def DMA0_setup(src:ptr32, dst:ptr32, nword:uint, control:uint):
        dma=ptr32(uint(DMA_BASE))
        dma[READ_ADDR] = uint(src)
        dma[WRITE_ADDR] = uint(dst)
        dma[TRANS_COUNT] = nword
        dma[CTRL_TRIG] = control
#
# Abort an transfer
#
    @staticmethod
    @micropython.viper
    def DMA_chan_abort(chan:uint):
        dma=ptr32(uint(DMA_BASE))
        dma[CHAN_ABORT] = 1 << chan
        while dma[CHAN_ABORT]:
            time.sleep_us(10)
#
# wait until the counter reaches zero
#
    @staticmethod
    @micropython.viper
    def DMA0_wait(limit:int):
        dma=ptr32(uint(DMA_BASE))
        wait = 5
        while (dma[TRANS_COUNT] > 0) and (limit > 0):
            time.sleep_us(wait)
            limit -= 1
            wait += 1
#
# encode font bitmap for text
#
    @staticmethod
    @micropython.viper
    def encode_charbitmap(bits:ptr8, size:int, control:ptr8, bg_buf:ptr8):
    #
        transparency = int(control[6])
        bm_ptr = 0
        bg_ptr = 0
        mask   = 0x80
    #
        while size:

            if bits[bm_ptr] & mask:
                bg_buf[bg_ptr] = int(control[3])
                bg_buf[bg_ptr + 1] = int(control[4])
                bg_buf[bg_ptr + 2] = int(control[5])
            else:
                if transparency & 1: # Dim background
                    pass
                    bg_buf[bg_ptr] >>= 1
                    bg_buf[bg_ptr + 1] >>= 1
                    bg_buf[bg_ptr + 2] >>= 1
                elif transparency & 2: # keep Background
                    pass
                else:
                    bg_buf[bg_ptr] = int(control[0])
                    bg_buf[bg_ptr + 1] = int(control[1])
                    bg_buf[bg_ptr + 2] = int(control[2])

            mask >>= 1
            if mask == 0: # mask reset & data ptr advance on byte exhaust
                mask = 0x80
                bm_ptr += 1
            size -= 1
            bg_ptr += 3
#
# encode 565 type data
#
    @staticmethod
    @micropython.viper
    def encode565(data:ptr8, pixels:int, buffer:ptr8):  #
        to = 0
        for i in range(0, pixels * 2, 2):
            buffer[to] = data[i + 1] & 0xf8
            buffer[to + 1] = ((data[i + 1] & 0x07) << 5) | ((data[i] >> 3) & 0x1c)
            buffer[to + 2] = data[i] << 3
            to += 3
#
# encode Windows BMP data with colortables
#
    @staticmethod
    @micropython.viper
    def encodeBMP(data:ptr8, pixels:int, colortable:ptr8, buffer:ptr8):
        dst = 0
        src = 0
        bits = pixels & 0xff
        size = pixels >> 8
        shift = 8 - bits
        mask = ((1 << bits) - 1)

        for i in range(size):
            offset = ((data[src] >> shift) & mask) * 4
            buffer[dst] = colortable[offset + 2]
            buffer[dst+1] = colortable[offset + 1]
            buffer[dst+2] = colortable[offset]

            shift -= bits
            dst += 3
            if shift < 0:
                shift = 8 - bits
                src += 1
#
# encode Windows BMP data with colortables
#
    @staticmethod
    @micropython.viper
    def encodeBMP8(data:ptr8, pixels:int, colortable:ptr8, buffer:ptr8):
        dst = 0
        for i in range(pixels):
            offset = data[i] * 4
            buffer[dst] = colortable[offset + 2]
            buffer[dst+1] = colortable[offset + 1]
            buffer[dst+2] = colortable[offset]
            dst += 3
#
# Set the address range for various draw commands and set the TFT for expecting data
#
# PIO version of
# SetXY: takes net about 50 µs including the call. Pretty slow
#
    @micropython.viper
    def setXY(self, x1: int, y1: int, x2: int, y2: int): ## set the adress range
        ar_setxy = self.ar_setxy
        ar_setxy[1] = (x1 >> 8) | 0x100
        ar_setxy[2] = x1 | 0x100
        ar_setxy[3] = (x2 >> 8) | 0x100
        ar_setxy[4] = x2 | 0x100
        ar_setxy[6] = (y1 >> 8) | 0x100
        ar_setxy[7] = y1 | 0x100
        ar_setxy[8] = (y2 >> 8) | 0x100
        ar_setxy[9] = y2 | 0x100

        self.sm_cmd_write.active(1)
        self.sm_cmd_write.put(ar_setxy, 0)
        self.sm_cmd_write.active(0)
#
# Set the address range for various draw commands and set the TFT for expecting data
#
# PIO version of
# adrPixel: takes net about 85 µs including the call. Pretty slow
#
    @micropython.viper
    def drawPixel(self, x: int, y: int, color:ptr8): ## set the adress range
        ar_drawPixel = self.ar_drawPixel
        ar_drawPixel[1] = (x >> 8) | 0x100
        ar_drawPixel[2] = x | 0x100
        ar_drawPixel[3] = ar_drawPixel[1]
        ar_drawPixel[4] = ar_drawPixel[2]
        ar_drawPixel[6] = (y >> 8) | 0x100
        ar_drawPixel[7] = y | 0x100
        ar_drawPixel[8] = ar_drawPixel[6]
        ar_drawPixel[9] = ar_drawPixel[7]

        ar_drawPixel[11] = color[0] | 0x100
        ar_drawPixel[12] = color[1] | 0x100
        ar_drawPixel[13] = color[2] | 0x100

        self.sm_cmd_write.active(1)
        self.sm_cmd_write.put(ar_drawPixel, 0)
        self.sm_cmd_write.active(0)
#
# PIO version of
# Fill screen by writing size pixels with the color given in data
# data must be 3 bytes of red, green, blue
# The area to be filled has to be set in advance by setXY
# The speed is 60 ns/pixel at 100MHz pio clock. Pretty fast
#
    @micropython.viper
    def fillSCR(self, data, pixels:int):
        self.sm_data_write_triple.active(1)
        TFT_IO.DMA0_setup(data, PIO0_BASE_TXF0, pixels, self.DMA_fill_control)
        TFT_IO.DMA0_wait(self.tx_limit)  # Wait for the transfer to finish
        self.sm_data_write_triple.active(0)
#
# Send data to the tft controller
#
    @micropython.viper
    def tft_data(self, data):
        self.sm_data_write_byte.active(1)
        self.sm_data_write_byte.put(data, 0)
        self.sm_data_write_byte.active(0)

    @micropython.viper
    def tft_data_DMA(self, data, size:int):
        self.sm_data_write_byte.active(1)
        TFT_IO.DMA0_setup(data, PIO0_BASE_TXF1, size, self.DMA_data_write_control)
        TFT_IO.DMA0_wait(self.tx_limit)  # Wait for the transfer to finish
        self.sm_data_write_byte.active(0)
#
# Send a command to the TFT controller
#
    @micropython.native
    def tft_cmd(self, cmd):
        self.sm_cmd_write.active(1)
        self.sm_cmd_write.put(cmd, 0)
        self.sm_cmd_write.active(0)
#
# Send a command and data to the TFT controller
# cmd is the command byte, data must be a bytearray object with the command payload,
# int is the size of the data
# For the startup-phase use this function.
#
    @micropython.native
    def tft_cmd_data(self, cmd, data, size):
        self.tft_cmd(cmd)
        self.tft_data(data)
#
# PIO version of send a command byte and read data from the TFT controller by DMA
# data must be a bytearray object, int is the size of the data.
# The speed is about 120 ns/byte. PIO speed 25 MHz. No luck
# at faster rates
#
    @micropython.viper
    def tft_read_cmd_data(self, cmd:int, data, size:int):
        self.sm_cmd_data_read.active(1)
        self.sm_cmd_data_read.put(size - 1)  # send the size
        self.sm_cmd_data_read.put(cmd, 0)  # send the command
        TFT_IO.DMA0_setup(PIO0_BASE_RXF3, data, size, self.DMA_data_read_control)
        TFT_IO.DMA0_wait(self.rx_limit)  # Wait for the transfer to finish
        self.sm_cmd_data_read.put(0xff, 0)  # reset direction
        self.sm_cmd_data_read.active(0)
#
# PIO version of send a command byte and read data from the TFT controller py polling
# data must be a bytearray object, int is the size of the data.
# The speed is about 14 µs/byte. Pretty slow.
#
    @micropython.viper
    def tft_read_cmd_data_poll(self, cmd:int, data, size:int):
        self.sm_cmd_data_read.active(1)
        self.sm_cmd_data_read.put(size - 1)  # send the size
        self.sm_cmd_data_read.put(cmd, 0)  # send the command
        for i in range(size):     # get the data
            data[i] = int(self.sm_cmd_data_read.get())
        self.sm_cmd_data_read.put(0xff, 0)  # reset direction
        self.sm_cmd_data_read.active(0)
        pass
#
# swap byte pairs in a buffer
# sometimes needed for picture data
#
    @micropython.viper
    def swapbytes(self, data:ptr8, len:int):               # bytearray, len(bytearray)
        for i in range(0, len, 2):
            data[i], data[i + 1] = data[i + 1], data[i]
#
# swap colors red/blue in the buffer
#
    @micropython.viper
    def swapcolors(self, data:ptr8, len:int):               # bytearray, len(bytearray)
        for i in range(0, len, 3):
            data[i], data[i + 2] = data[i + 2], data[i]

