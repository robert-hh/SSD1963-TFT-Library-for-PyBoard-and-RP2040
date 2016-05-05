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
        self.unused = height - self.g_height # unused area at the bottom
        # set scroll area in relation to the font size, full size
        self.tft.setScrollArea(0 , self.g_height, self.unused)
        self.tft.setTextStyle(fgcolor = (190, 190, 190), bgcolor = (0, 0, 0), font = self.font)
        self.fgcolor = [255, 255, 255]
        self.bgcolor = [0, 0, 0]
        self.scaling = 0.75
        self.inv = False
        self.underscore = False
        self.scroll_first = 1
        self.scroll_last = self.text_rows
        self.state = 0
        self.tft.printClrSCR()
        self.tft.backlight(100) # Backlight on
        self.saved_row = self.saved_col = 1
        
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
        # col, row are 1-based, TFT cooedinates are 0-based
        self.tft.setTextPos((col - 1) * self.hor, (row - 1) * self.vert , scroll = False)

    def get_row_col(self): # get column and row from tft text position 
        x, y = self.tft.getTextPos()
        return (y // self.vert) + 1, (x // self.hor) + 1
        
    def print_char(self, c):  # print a char
        rtnval = ""
        if self.state == 0:
            if c == "\n": # newline
                self.tft.printNewline(True)
            elif c == "\r": # Carriage return
                self.tft.printCR()
            elif c == "\t": # tab
                row,col = self.get_row_col()
                self.tft.printString(" " * (8 - (col % 8)))
            elif c == "\b": # Backspace
                row, col = self.get_row_col()
                if col > 1: 
                    self.goto(row, col - 1)
            elif ord(c) == 0x0c: # Form feed = clear screen
                self.tft.printClrSCR()
            elif ord(c) == 0x1b:
                self.state = 1
            elif ord(c) == 0x9b:
                self.state = 2
                self.p_string = ""
            else: # just print the char
                size = self.tft.printChar(c)
                if self.underscore:
                    x,y = self.tft.getTextPos(False)
                    self.tft.drawHLine(x - size, y + self.vert - 1, size, self.fgcolor)
        elif self.state == 1: # waiting for [ as next char
            if c == "[":
                self.state = 2
                self.p_string = ""
            elif c == '7': # save Cursor
                self.saved_row, self.saved_col = self.get_row_col()
                self.state = 0
            elif c == '8': # restore Cursor
                self.goto(self.saved_row, self.saved_col)
                self.state = 0
            elif c == 'D': # Scroll Down
                row,col = self.get_row_col() # get actual cursor position
                self.tft.scroll(-self.vert) # Roll screen down
                self.goto(self.scroll_first, 1) # clear first line
                self.tft.printClrLine(2)
                self.goto(row,col) # restore cursor
                self.state = 0
            elif c == 'M': # Scroll Up
                row,col = self.get_row_col() # get actual cursor position
                self.tft.scroll(self.vert) # roll screen up
                self.goto(self.scroll_last, 1) # goto last line
                self.tft.printClrLine(2) # and clear it
                self.goto(row,col) # restore cursor
                self.state = 0
            else:
                self.tft.printChar('\x1b')
                self.tft.printChar(c)
                self.state = 0
        elif self.state == 2: # collecting command data
            if c.isalpha(): # command collection finished; execute it
                self.state = 0
                cmd = c
                parmlist = self.p_string.split(";")
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
                        row, col = self.get_row_col()
                        for r in range(row, self.scroll_last + 1): # clear lines to the end of scrollable area
                            self.goto(r, 1)
                            self.tft.printClrLine(2)
                        self.goto(row, col)
                    elif mode == 1: # clear up
                        row, col = self.get_row_col()
                        for r in range(self.scroll_first, row): # clear lines from the start of scrollable area
                            self.goto(r, 1)
                            self.tft.printClrLine(2)
                        self.goto(row, col)
                    elif mode == 2: # clear screen
                        self.tft.printClrSCR()
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
                        elif mode == 5: # status is always OK
                            print("\x1b[0n")
                elif cmd == "m":  # set text attributes
                    if parmlist[0] == "": # replace an empty parmlist with reset value
                        parmlist[0] = "0"
                    for parm in parmlist:
                        val = int(parm)
                        if val == 0: # default
                            self.fgcolor = [255, 255, 255]
                            self.bgcolor = [0, 0, 0]
                            self.scaling = 0.75
                            self.inv = False
                            self.underscore = False
                        if val == 1: # bright
                            self.scaling = 1
                        elif val == 2: # dim
                            self.scaling = 0.4
                        elif val == 3: # standard
                            self.scaling = 0.75
                        elif val == 4: # underscore
                            self.underscore = True
                        elif val == 7: # reverse
                            self.inv = True
                        elif 30 <= val <= 37:
                            self.fgcolor = self.colortable[val % 10]
                        elif 40 <= val <= 47:
                            self.bgcolor = self.colortable[val % 10]
                    fgcolor = (int(self.fgcolor[0] * self.scaling),                                 
                               int(self.fgcolor[1] * self.scaling),
                               int(self.fgcolor[2] * self.scaling))
                    bgcolor = (int(self.bgcolor[0] * self.scaling), 
                               int(self.bgcolor[1] * self.scaling),
                               int(self.bgcolor[2] * self.scaling))
                    if self.inv:
                        fgcolor, bgcolor = bgcolor, fgcolor
                    self.tft.setTextStyle(fgcolor=fgcolor, bgcolor=bgcolor)
                elif cmd == "r":    # Scrolling
                    if parmlist[0] == "": # Scroll full screen
                        self.tft.setScrollArea(0 , self.g_height, self.unused)
                        self.scroll_first = 1
                        self.scroll_last = self.text_rows
                    else:
                        if len(parmlist) > 1: # must have two parameters
                            self.scroll_first = int(parmlist[0])
                            self.scroll_last = int(parmlist[1])
                            if (self.scroll_first >= 1
                                and self.scroll_first <= self.scroll_last 
                                and self.scroll_last <= self.text_rows): # Check order & size
                                
                                tfa = max((self.scroll_first - 1) * self.vert, 0)
                                vsa = (self.scroll_last - self.scroll_first + 1) * self.vert
                                bfa = max(self.g_height - tfa - vsa, 0) + self.unused
                                self.tft.setScrollArea(tfa, vsa, bfa)
                                                       
                else: # not implemented
                    self.tft.printString('\x1b[' + self.p_string + cmd)
            else: # not terminated, collect parameters
                self.p_string += c
        else:
            pass            
        return rtnval

    def printStr(self, s): # this is the main print function
        if s:
            self.cursor() # toggle cursor off
            for c in s:
                self.print_char(c)
            self.cursor() # toggle cursor on

def test():
    tty = VT100(font7hex)
    cmd = ""
    while cmd != "q":
        tty.printStr('\x0c')
        tty.printStr("Far far away, behind the word mountains, far from the\r\n")
        tty.printStr("countries Vokalia and Consonantia, there live the blind\r\n")
        tty.printStr("texts. Separated they live in Bookmarksgrove right at\r\n")
        tty.printStr("the coast of the Semantics, a large language ocean.\r\n")
        tty.printStr("A small river named Duden flows by their place and\r\n")
        tty.printStr("supplies it with the necessary regelialia. It is a\r\n")
        tty.printStr("paradisematic country, in which roasted parts of\r\n")
        tty.printStr("sentences fly into your mouth. Even the all-powerful\r\n")
        tty.printStr("Pointing has no control about the blind texts it is an\r\n")
        tty.printStr("almost unorthographic life. One day however a small line\r\n")
        tty.printStr("of blind text by the name of Lorem Ipsum decided to \r\n")
        tty.printStr("leave for the far World of Grammar. The Big Oxmox advised\r\n")
        tty.printStr("her not to do so, because there were thousands of bad\r\n")
        tty.printStr("Commas, wild Question Marks and devious Semikoli, but\r\n")
        tty.printStr("the Little Blind Text didn't listen. \r\n")
        tty.printStr("She packed her seven versalia, put her initial into the\r\n")
        tty.printStr("belt and made herself on the way. When she reached the\r\n")
        tty.printStr("first hills of the Italic Mountains, she had a last view\r\n")
        tty.printStr("back on the skyline of her hometown Bookmarksgrove, the\r\n")
        tty.printStr("headline of Alphabet Village and the subline of her\r\n")
        tty.printStr("own road, the Line Lane. Pityful a rethoric question ran\r\n")
        tty.printStr("over her cheek.\r\n")
        tty.printStr("\r\n")
        tty.printStr("  ----------- VT100 emulation test -------------- \r\n") 
        tty.printStr("If the text starts with [, an ESC will be added upfront\r\n")
        tty.printStr("If the text starts with \\, this will be replced by ESC\r\n")
        tty.printStr("If the text ends with -, it will be printed w/o CR-LF\r\n")
        tty.printStr("Otherwise the text will be printed, followed by CR-LF\r\n")
        cmd = " "
        while cmd != "q" and cmd != "":
            cmd = input("Command: ")
            if cmd != "":
                if cmd[0] == "[":
                    tty.printStr("\x1b" + cmd)
                elif cmd[0] == "\\":
                    tty.printStr("\x1b" + cmd[1:])
                else:
                    if cmd[-1] == "-":
                        tty.printStr(cmd)
                    else:
                        tty.printStr(cmd + "\r\n")
                

test()
