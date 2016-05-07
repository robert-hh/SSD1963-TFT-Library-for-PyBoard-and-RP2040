#
# test for icons

import tft
import checkbox
import radiobutton
import switch
import sliderpath
import sliderhandle


mytft = tft.TFT()
mytft.backlight(100)
mytft.clrSCR((255,255,255))

checkbox.draw(20, 20, 0, mytft.drawBitmap)
checkbox.draw(20, 60, 1, mytft.drawBitmap)
checkbox.draw(20, 100, 2, mytft.drawBitmap)

radiobutton.draw(20, 150, 1, mytft.drawBitmap)
radiobutton.draw(60, 150, 0, mytft.drawBitmap)
radiobutton.draw(100, 150, 0, mytft.drawBitmap)

switch.draw(150, 20, 0, mytft.drawBitmap)
switch.draw(150, 60, 1, mytft.drawBitmap)

sliderpath.draw(300, 130, 0, mytft.drawBitmap)
sliderhandle.draw(300, 150, 1, mytft.drawBitmap)
