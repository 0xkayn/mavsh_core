from connection import *

gcs = MavshGCS('/dev/ttyACM0')
print(gcs)
heartbeat = gcs.wait_heartbeat()
print(heartbeat)
# i think we need to init inside the loop
import sys

try:
    gcs.mavsh_init()
    status = gcs.message_loop()
    print(status)
    gcs.shell_loop(status)
except KeyboardInterrupt:
    print(gcs.request_mavsh_shutdown())

