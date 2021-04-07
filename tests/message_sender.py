from pymavlink import mavutil
from pymavlink.dialects.v20 import ardupilotmega as mavsh
import serial
import pdb
s = serial.Serial('/dev/ttyACM0')


companion = mavsh.MAVLink(  
    s,
    srcSystem=255,
    srcComponent=1,
)

#companion = mavutil.mavlink_connection('/dev/ttyACM0', source_system=255,source_component=190)
#print(dir(companion))
#mavlink.MAV_TYPE_ONBOARD_CONTROLLER
companion.heartbeat_send(
    18, # MAV_TYPE - ONBOARD_CONTROLLER
    8, #MAV_AUTOPILOT - INVALID/companion computer
    2, #MAV_MODE_FLAG - test enabled
    0, #CUSTOM_MODE - empty?
    3, # SYSTEM_STATUS - STANDBY
)

#print(companion.mav.srcComponent)
companion.mavsh_init_send(
    255, # self.gcs_sysid
    1, # self.gcs_compid
    1, # target_system - rpi's sysid
    191, # target_component - rpi's compid
    mavsh.MAVSH_INIT
)

companion.mavsh_ack_send(
    255,
    1,
    1,
    191,
    0
)
companion.mavsh_synack_send(
    255,
    1,
    1,
    191
)

companion.mavsh_exec_send(
    255, # origin sysid - should always be 255 bc gcs
    1, # origin compid - 1 bc gcs
    1,  # target sysid - 1 bc MAV
    191, # target compid - 200
    0, # MAVSH_STATUS - probably needs to be removed
    b"nmap -sV 172.16.123.172" # payload  
)

def mavsh_loop(self):
        #self.request_data()
        #self.wait_heartbeat()

        while True:                     
            mes = self.conn.recv_match(blocking=False)              
            while not mes:
                mes = self.conn.recv_match(blocking=False)

            mes_type = mes.get_type()
            if mes_type == "MAVSH_INIT":
                print(mes)
            elif mes_type == "MAVSH_ACK":
                print(mes)
            elif mes_type == "MAVSH_EXEC":
                print(mes)
            elif mes_type == "MAVSH_RESPONSE":
                self.handle_mavsh_response(mes)
            elif mes_type == "HEARTBEAT":
                print(mes.type)
            elif mes_type == "BAD_DATA":
                pass
            else:                
                pass
