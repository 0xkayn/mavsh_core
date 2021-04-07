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

    def __init__(self, device='/dev/ttyS0', sysid=1, compid=191):
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
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.mavsh_loop())
        self.active = False        

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


    async def handle_mavsh_init(self, mes):
        if self.active:
            print('MAVSH Active')
        elif not self.active:
            print('MAVSH_inactive')
            
            # make sure the packet is for us before turning on mavsh            
            print(self.conn.param_state)
            print(self.conn.source_system)
            print(self.conn.source_component)            
            print(self.conn.target_system) # this will be 0/broadcast by default so all systems will recv the messages - need to control this param on both sides
            print(self.conn.target_component) # 

            if (mes.target_system == self.sysid) and (mes.target_component == self.compid):

                print('MAVSH now active')
                self.active = True            

        print(mes)
        
    async def handle_mavsh_ack(self, mes):
        print(mes)    
    
     
    #async def testsh(self, mes):
        

    async def handle_mavsh_exec(self, mes):         
        
        async def run_cmd(cmd):
            # shlex.split will escape characters used for cmd injection
            # but create_subprocess_shell requires a string so we join the list
            cmd = " ".join(shlex.split(cmd))
            p = await asyncio.create_subprocess_shell(cmd,
                stdin=PIPE, 
                stdout=PIPE, 
                stderr=STDOUT
            )
            
            command_started = time.time()
            
            now = time.time()
            if now - command_started > 1.5:
                self.conn.mav.mavsh_response_send(
                    self.sysid,
                    self.compid,
                    self.conn.target_system,
                    self.conn.target_component,
                    mlink.MAVSH_EXECUTING,
                    b''
                )

            return (await p.communicate())[0]
        
        command_started = time.time()
        result = await run_cmd(mes.payload)
        #command = self.loop.create_future()

        #command = self.loop.create_task(run_cmd(mes.payload))
        
        command_started = time.time()
        # send a response message every 2 seconds to let us know if the command has finished
        # this will be particularly useful when showing when a command/scan completes on my OSD        
        #import pdb
        print(result)
        #pdb.set_trace()

        """
        while not command.done():                    
            now = time.time()
            if now - command_started > 1.5:
                self.conn.mav.mavsh_response_send(
                    self.sysid,
                    self.compid,
                    self.conn.target_system,
                    self.conn.target_component,
                    mlink.MAVSH_EXECUTING,
                    b''
                )
        """
        
        if len(result) > 154:
            def chunk_result(res):        
                # chunks the response message into a max size of 154 bytes          
                return [res[i:i+154] for i in range(0, len(res), 154)]
            
            response = chunk_result(result)
        else :
            response = result

        for chunk in response:
            self.conn.mav.mavsh_response_send(
                self.sysid,
                self.compid,
                self.conn.target_system,
                self.conn.target_component,
                0, # mlink.complete
                bytes(chunk)
            )    

        return response

    async def handle_mavsh_response(self, mes):
        print(mes)
    
    async def tester(self, mes):
        print(mes)
    
    async def mavsh_loop(self):
                               
        while True: 
            self.send_heartbeats()                    
            mes = self.conn.recv_match(blocking=False)              
            while not mes:
                mes = self.conn.recv_match(blocking=False)
            
            mes_type = mes.get_type()
            if mes_type == "MAVSH_INIT":
                await self.loop.create_task(self.handle_mavsh_init(mes))
                #print(self.handle_mavsh_init(mes))
            elif mes_type == "MAVSH_ACK":
                await self.loop.create_task(self.handle_mavsh_ack(mes))
                #print(self.handle_mavsh_ack(mes))
            elif mes_type == "MAVSH_EXEC":
                print(await self.loop.create_task(self.handle_mavsh_exec(mes)))
                #print( (await self.handle_mavsh_exec(mes)) )                
                #print(self.loop.create_task(self.run_cmd(mes.payload)))
                #print(self.handle_mavsh_exec(mes).decode)
            elif mes_type == "MAVSH_RESPONSE":
                await self.loop.create_task(self.handle_mavsh_response(mes))
                #print(self.handle_mavsh_response(mes))
            elif mes_type == "HEARTBEAT":
                print(mes)
            elif mes_type == "BAD_DATA":
                pass
            else:                
                pass

a = Companion()
a.wait_heartbeat()
a.loop.run_forever()
#a.mavsh_loop()
