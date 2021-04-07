import pdb
import sys
import time
import shlex
import serial
import asyncio
from pymavlink import mavutil
from asyncio.subprocess import PIPE, STDOUT
from pymavlink.dialects.v20 import ardupilotmega as mlink


# integrate this into mavproxy later
class Companion():

    def __init__(self, device='/dev/ttyS0', sysid=1, compid=200):
        #super().__init__(device=device, source_system=1, source_component=200)                
        self.sysid = sysid
        self.compid = compid
        # dont create the connection right when the object is created..? or do we want to... idk yet
        self.conn = mavutil.mavserial(
            device,
            source_system=self.sysid,
            source_component=self.compid,
            baud=57600
            #baudrate=115200 # could cause a bug, refer to line 918 of mavutil.py if so
        )        
        
        self.last_heartbeat_sent = 0
    
    def send_heartbeats(self):
        now = time.time()
        if now - self.last_heartbeat_sent > 0.5:
            self.last_heartbeat_sent = now
            self.conn.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                0
            )

    
    def wait_heartbeat(self, blocking=True, timeout=None):
        """
        wait for a heartbeat so we know the target system IDs
        sets: self.conn.target_system & self.conn.target_component
        """
        return self.conn.recv_match(type='HEARTBEAT', blocking=blocking, timeout=timeout)
    
    def request_data(self):
        
        self.conn.mav.request_data_stream_send(
            self.conn.target_system, 
            self.conn.target_component, 
            mavutil.mavlink.MAV_DATA_STREAM_ALL, 
            4, 
            1        
        )
        return 


    def handle_mavsh_init(self, mes):
        return mes    
        
    def handle_mavsh_ack(self, mes):
        return mes
    
            
    async def run_cmd(cmd):
        # shlex.split will escape characters used for cmd injection
        # but create_subprocess_shell requires a string so we join the list
        cmd = " ".join(shlex.split(cmd))
        p = await asyncio.create_subprocess_shell(cmd,
            stdin=PIPE, 
            stdout=PIPE, 
            stderr=STDOUT
        )
        return (await p.communicate())[0] 

    async def handle_mavsh_exec(self, mes):         
        response = await run_cmd(msg.payload)
        self.conn.mavsh_response_send(
            self.sysid,
            self.compid,
            self.conn.target_system,
            self.conn.target_component,
            0,
            response
        )
        print(response)
    
    def chunk_response(self,res):
        pass

    def handle_mavsh_response(self, mes):
        return mes
      
    
    def mavsh_loop(self):
        #self.request_data()
        #self.wait_heartbeat()        
        
        while True:                     
            mes = self.conn.recv_match(blocking=False)              
            while not mes:
                mes = self.conn.recv_match(blocking=False)
            
            mes_type = mes.get_type()
            if mes_type == "MAVSH_INIT":
                print(self.handle_mavsh_init(mes))
            elif mes_type == "MAVSH_ACK":
                print(self.handle_mavsh_ack(mes))
            elif mes_type == "MAVSH_EXEC":
                print(self.handle_mavsh_exec(mes).decode)
            elif mes_type == "MAVSH_RESPONSE":
                print(self.handle_mavsh_response(mes))
            elif mes_type == "HEARTBEAT":
                print(mes)
            elif mes_type == "BAD_DATA":
                pass
            else:                
                pass

a = Companion()
a.wait_heartbeat()
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(a.mavsh_loop())
finally:
    loop.close()
#a.mavsh_loop()
