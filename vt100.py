#
# VT100 terminal emulation for the TFT lib
#
import os, gc, pyb

import tft 
from font7hex import font7hex

DIM_BG  = const(1)  # dim background data for text
KEEP_BG = const(2)  # keep background data for text
INV_BG  = const(4)  # invert the background data for text
INV_FG  = const(8)  # use the inverted background data for text color


class VT100:

    colortable = {
        0 : [0,0,0],        # black
        1 : [255, 0, 0],    # red
        2 : [0, 255, 0],    # green
        3 : [255, 255, 0],  # yellow
        4 : [0, 0, 255],    # blue
        5 : [255, 0, 255],  # magenta
        6 : [0, 255, 255],  # cyan
        7 : [255, 255, 255] # white
    }
    
    def __init__(self, font):
        self.tft = tft.TFT("SSD1963", "LB04301", tft.LANDSCAPE)
        self.font = font
        self.g_width, height = self.tft.getScreensize()
        self.vert, self.hor, self.nchar, self.firstchar = font.get_properties()
        self.text_rows = height // self.vert      # determine text lines
        self.text_cols = self.g_width // self.hor # determine tex cols
        self.g_height = self.text_rows * self.vert # used height for text
        self.vsa = self.g_height
        self.bsa = 0
        self.tsa = 0
        self.bottom = height - self.g_height # unused area at the bottom
        # set scroll area in relation to the font size, full size
        self.tft.setScrollArea(self.tsa, self.g_height, self.bottom + self.bsa) 
        self.tft.setTextStyle(fgcolor = (190, 190, 190), bgcolor = (0, 0, 0), font = self.font)
        self.state = 0
        self.clear_screen()
        self.tft.backlight(100) # Backlight on
        self.saved_row = self.saved_col = 1
        
    def clear_screen(self): # clear screen
        self.tft.printClrSCR(2)
        self.goto(1, 1)
        
    def cursor(self):  #  toggle cursor
        x,y = self.tft.getTextPos()
        # create/delete a block cursor by writing a space with backgound inversion
        self.tft.setTextStyle(transparency=INV_BG)
        self.tft.printChar(" ")
        self.tft.setTextPos(x, y)
        self.tft.setTextStyle(transparency=0)
        
    def goto(self, row, col): # set TFT-coordinates to text coordinates
        col = max(1, min(self.text_cols, col)) # check for limits
        row = max(1, min(self.text_rows, row))
        self.text_col = col
        self.text_row = row
        # col, row are 1-based, TFT cooedinates are 0-based
        y = ((row - 1) * self.vert + self.tft.getScrollStart()) % self.g_height
        print(row, self.tft.getScrollStart(), self.g_height, self.vert, y)
        self.tft.setTextPos((col - 1) * self.hor, y, scroll = False)

        
    def get_row_col(self): # get column and row from tft text position 
        x,y = self.tft.getTextPos()
        y = (y - self.tft.getScrollStart()) % self.g_height
        self.text_col =  (x // self.hor) + 1
        self.text_row =  (y // self.vert) + 1
        return self.text_row, self.text_col
        
    def print(self, c):  # print a char
        rtnval = ""
        if self.state == 0:
            if c == "\n": # newline
                self.tft.printNewline()
            elif c == "\r": # Carriage return
                self.tft.printCR()
            elif c == "\t": # tab
                col = self.text_y
                self.tft.printString(" " * (8 - (self.text_y % 8)))
            elif c == "\b": # Backspace
                if self.text_x > 1:
                    self.goto(self.text_x - 1, self.text_y)
            elif ord(c) == 0x0c: # Form feed = clear screen
                self.clear_screen()
            elif ord(c) == 0x1b:
                self.state = 1
            elif ord(c) == 0x9b:
                self.state = 2
                self.p_string = ""
            else: # just print the char
                self.tft.printChar(c)
        elif self.state == 1: # waiting for [ as next char
            if c == "[":
                self.state = 2
                self.p_string = ""
            else:
                self.state = 0
        elif self.state == 2: # collecting command data
            if c.isalpha(): # command collection finished; execute it
                self.state = 0
                cmd = c
                parmlist = self.p_string.split(";")
                print("Command", self.p_string, c, parmlist)
                if cmd in ("H", "f"): # set cursor
                    row = col = 1
                    if len(parmlist) > 1:
                        row = int(parmlist[0])
                        col = int(parmlist[1])
                    self.goto(row, col)
                elif cmd == "A": # up
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                    else:
                        mode = 1
                    row, col = self.get_row_col()
                    row -= mode
                    if row < 1: 
                        row = 1
                    self.goto(row, col)
                elif cmd == "B": # down
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                    else:
                        mode = 1
                    row, col = self.get_row_col()
                    row += mode
                    if row > self.text_rows: 
                        row = self.text_rows
                    self.goto(row, col)
                elif cmd == "C": # right
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                    else:
                        mode = 1
                    row, col = self.get_row_col()
                    col += mode
                    if col > self.text_cols: 
                        col = self.text_cols
                    self.goto(row, col)
                elif cmd == "D": # left
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                    else:
                        mode = 1
                    row, col = self.get_row_col()
                    col -= mode
                    if col < 1: 
                        col = 1
                    self.goto(row, col)
                elif cmd == "K": # erase line
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                    else:
                        mode = 0
                    if mode == 0: # clear to EOL
                        self.tft.printClrLine(0)
                    elif mode == 1: # clear to BOL
                        self.tft.printClrLine(1)
                    elif mode == 2: # clear Line
                        self.tft.printClrLine(2)
                elif cmd == "J":  # clear screen
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                    else:
                        mode = 0
                    if mode == 0: # clear down
                        self.tft.printClrSCR(0)
                    elif mode == 1: # clear up
                        self.tft.printClrSCR(1)
                    elif mode == 2: # clear screen
                        self.clear_screen()
                elif cmd == "s":  # save cursor
                    self.saved_row, self.saved_col = self.get_row_col()
                elif cmd == "u":  # restore cursor
                    self.goto(self.saved_row, self.saved_col)
                elif cmd == "n":  # report
                    if parmlist[0] != "":
                        mode = int(parmlist[0])
                        if mode == 6:
                            row, col = self.get_row_col()
                            print("\x1b[{};{}R".format(row, col))
                elif cmd == "m":  # set text attributes
                    if parmlist[0] == "": # replace an empty parmlist with reset value
                        parmlist[0] = "0"
                    for parm in parmlist:
                        val = int(parm)
                        fgcolor = [255, 255, 255]
                        bgcolor = [0, 0, 0]
                        scaling = 0.75
                        inv = False
                        if val == 0: # default
                            fgcolor = [255, 255, 255]
                            bgcolor = [0, 0, 0]
                            scaling = 0.75
                        if val == 1: # bright
                            scaling = 1
                        elif val == 2: # dim
                            scaling = 0.4
                        elif val == 7: # reverse
                            inv = True
                        elif 30 <= val <= 37:
                            fgcolor = self.colortable[val % 10]
                        elif 40 <= val <= 47:
                            bgcolor = self.colortable[val % 10]
                    for i in range (3): # scale brightness
                        fgcolor[i] = int(fgcolor[i] * scaling)
                        bgcolor[i] = int(bgcolor[i] * scaling)
                    if inv:
                        fgcolor, bgcolor = bgcolor,fgcolor
                    self.tft.setTextStyle(fgcolor=fgcolor, bgcolor=bgcolor)

                else: # not implented
                    pass
            else: # not terminated, collect parameters
                self.p_string += c
        else:
            pass            
        return rtnval

    def printStr(self, s):
        if s:
            self.cursor() # toggle cursor off
            for c in s:
                self.print(c)
            self.cursor() # toggle cursor on

def main():
    tty = VT100(font7hex)
    cmd = ""
    while cmd != "q":
        tty.printStr('\x0c')
        tty.printStr("Lorem ipsum dolor sit amet, consectetuer adipiscing elit.\r\n")
        tty.printStr("Aenean commodo ligula eget dolor. Aenean massa.\r\n")
        tty.printStr("Cum sociis natoque penatibus et magnis dis parturient,\r\n")
        tty.printStr("nascetur ridiculus mus. Donec quam felis, ultricies\r\n")
        tty.printStr("nec, pellentesque eu, pretium quis, sem.\r\n")
        tty.printStr("Nulla consequat massa quis enim. Donec pede justo,\r\n")
        tty.printStr("vel, aliquet nec, vulputate eget, arcu. In enim justo,\r\n")
        tty.printStr("rhoncus ut, imperdiet a, venenatis vitae, justo.\r\n")
        tty.printStr("Felis eu pede mollis pretium. Integer tincidunt.\r\n")
        tty.printStr("Cras dapibus. Vivamus elementum semper nisi.\r\n")
        tty.printStr("Aenean vulputate eleifend tellus. Aenean leo ligula,\r\n")
        tty.printStr("porttitor eu, consequat vitae, eleifend ac, enim.\r\n")
        tty.printStr("Aliquam lorem ante, dapibus in, viverra quis, feugiat a, \r\n")
        tty.printStr("tellus. Phasellus viverra nulla ut metus varius laoreet.\r\n")
        tty.printStr("Quisque rutrum. Aenean imperdiet. Etiam ultricies nisi vel \r\n")
        tty.printStr("augue. Curabitur ullamcorper ultricies nisi.\r\n")
        tty.printStr("Nam eget dui. Etiam rhoncus. Maecenas tempus, tellus eget\r\n")
        if True:
            tty.printStr("condimentum rhoncus, sem quam semper libero, sit amet\r\n")
            tty.printStr("sem neque sed ipsum. Nam quam nunc, blandit vel, luctus\r\n")
            tty.printStr("pulvinar, hendrerit id, lorem. Maecenas nec odio et ante\r\n")
            tty.printStr("tincidunt tempus. Donec vitae sapien ut libero venenatis\r\n") 
            tty.printStr("faucibus. Nullam quis ante. Etiam sit amet orci eget eros \r\n")
            tty.printStr("faucibus tincidunt. Duis leo. Sed fringilla mauris sit. \r\n")
            tty.printStr("Donec sodales sagittis magna.\r\n")
            tty.printStr("Sed consequat, leo eget bibendum sodales, augue velit\r\n")
        tty.printStr("\x1b[K")
        cmd = " "
        while cmd != "q" and cmd != "":
            cmd = input("Text or Command, which starts with '[': ")
            if cmd[0] == "[":
                tty.printStr("\x1b" + cmd)
            else:
                tty.printStr(cmd)

main()
