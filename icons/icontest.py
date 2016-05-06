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


mytft.drawCircle(250, 216, 16, (150,150,150))
mytft.drawCircle(250, 216, 15, (0,0,0))
mytft.fillCircle(250, 216, 6, (0,255,0))
mytft.drawCircle(300, 216, 16, (150,150,150))
mytft.drawCircle(300, 216, 15, (0,0,0))
mytft.drawCircle(350, 216, 16, (150,150,150))
mytft.drawCircle(350, 216, 15, (0,0,0))

