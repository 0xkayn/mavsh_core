from pymavlink import mavutil
from pymavlink.dialects.v20 import ardupilotmega as mavsh
import time
#conn = serial.Serial('/dev/ttyACM0')
mav = mavutil.mavlink_connection('/dev/ttyACM0')
mav.wait_heartbeat()
#print(mav.target_system)
#print(mav.target_component)
#print(mav.source_component)
#time.sleep(2)
while True:
    msg = mav.recv_match(blocking=False)
    while not msg:
        msg = mav.recv_match(blocking=False)
    msg_type = msg.get_type()
    if msg_type == "MAVSH_INIT":
        print(msg)
    elif msg_type == "HEARTBEAT":
        print(msg)
    elif msg_type == "MAVSH_RESPONSE":
        print(msg)
    else:
        pass

