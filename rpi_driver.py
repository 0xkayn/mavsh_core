from connection import *

rpi = MavshCompanion('/dev/ttyS0')
print(rpi)
rpi.message_loop()