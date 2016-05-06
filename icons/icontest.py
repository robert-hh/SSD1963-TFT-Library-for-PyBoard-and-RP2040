#
# test for icons

import tft
import checkbox
import radiobutton


mytft = tft.TFT()
mytft.backlight(100)
mytft.clrSCR((255,255,255))

mytft.drawBitmap(50, 50, *checkbox.get_icon(0))
mytft.drawBitmap(50,100, *checkbox.get_icon(1))
mytft.drawBitmap(50,150, *checkbox.get_icon(2))

mytft.drawBitmap(50,200, *radiobutton.get_icon(0))
mytft.drawBitmap(100,200, *radiobutton.get_icon(1))
mytft.drawBitmap(150,200, *radiobutton.get_icon(1))

