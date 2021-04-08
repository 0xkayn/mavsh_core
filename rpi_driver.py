from connection import *
from mavsh_exceptions import * 
import asyncio

rpi = MavshCompanion('/dev/ttyS0')
print(rpi)
try:
    rpi.message_loop()
    rpi.loop.run_forever()
    
except SessionExistsException:
    pass
