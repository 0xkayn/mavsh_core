import shlex 
from connection import *          
from threading import Thread
from pymavlink.dialects.v20 import ardupilotmega as mlink
import asyncio 
import os

<<<<<<< HEAD
class MAVSH:

    def __init__(self):
        self._status = mlink.MAVSH_INACTIVE #|| "inactive"
        self._input_ready = False        
        self._prompt = 'MAVSH> '
        self.modes = {
            'remote':'',
            'local':'!',
            'menu':'['
        }

        self.mav = MavshGCS('udp:0.0.0.0:8888')
        self.conn = self.mav.conn
    
    # do a sanity check for a mav being a gcs or companion


    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, status):
        if status != mlink.MAVSH_INACTIVE or status != mlink.MAVSH_ACTIVE:
            return -1        
        else:
            self._status = status
        return

    
    def print_banner(self):
        
        print('''

            __  ______ _    _______ __  __
           /  |/  /   | |  / / ___// / / /
          / /|_/ / /| | | / /\__ \/ /_/ / 
         / /  / / ___ | |/ /___/ / __  /  
        /_/  /_/_/  |_|___//____/_/ /_/   
                Version 0.1
        ''')

    def display_help(self):
    
        print('''
        help> 
        c: Display known connections
        h: Display this menu
        r: Reconnect to mav # not working yet
        ''')
    
    def get_input(self):
        try:
            inp = input("MAVSH> ")        
            return " ".join(shlex.split(inp))
        except Exception:
            print(Exception)
    """
    def parse_input(self, s):
        if cmd[0] == "!":
            os.system(cmd[1:])
            continue
        elif cmd[0] == "-":
            
        else:                
            self.mav.send_mavsh_exec(self.status, cmd) 
    """

    def mavsh_post_init(self):
        
        while self.mav.status != mlink.MAVSH_ACTIVE:           
            self.mav.send_heartbeats()                 

            mes = self.conn.recv_match(blocking=False)              
            while not mes:
                mes = self.conn.recv_match(blocking=False)
            mes_type = mes.get_type()

            if mes_type == "MAVSH_ACK":                
                self.mav.handle_mavsh_ack(mes)            

            elif mes_type == "MAVSH_SYNACK":
                print(mes)
                if self.mav.status == mlink.MAVSH_INACTIVE:                                        
                    self.mav.status = mlink.MAVSH_ACTIVE
                    self.status = mlink.MAVSH_ACTIVE
                    return mlink.MAVSH_ACTIVE                    
            
            elif mes_type == "MAVSH_SHUTDOWN":
                print(mes)

            elif mes_type == "HEARTBEAT":                
                self.mav.handle_heartbeat(mes)                
            
            else:                                
                pass
    
    async def mavsh_loop(self):
        self.input_ready = True

        while True:
            #self.send_heartbeats()
            
            if self.input_ready == True:
                try:                    
                    cmd = self.get_input()
                    if cmd[0] == "!":
                        os.system(cmd[1:])
                        continue
                    elif cmd[0] == "[":
                        # this will be the help/modes menu
                        
                       
                        try:                            
                            self.display_help()                            
                            while True:
                                i = input("help> ")
                                if len(i) > 1:
                                    print("Invalid option")
                                    continue
                                
                                if i.lower() == "c":
                                    print(self.mav.components)
                                elif i.lower() == "h":
                                    self.display_help()

                        except KeyboardInterrupt:
                            print()
                            continue

                    else:                
                        self.mav.send_mavsh_exec(self.status, cmd)                        
                except AttributeError:
                    pass            
            
            mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=False)
            while not mes:  
                mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=False)

            mes_type = mes.get_type()

            if mes_type == "MAVSH_RESPONSE":
                await self.mav.handle_mavsh_response(mes)
                if mes.cmd_status == mlink.MAVSH_EXECUTING:                    
                    self.input_ready = False                                        
                    #await self.handle_mavsh_response(mes)
                    
                elif mes.cmd_status == mlink.MAVSH_IDLE:
                    self.input_ready = True

                
            else:                
                print(mes)

    def start(self):
        self.print_banner()
        ht = Thread(target=self.mav.heartbeat_loop, args=())
        ht.start()
        self.mav.mavsh_init()
        
        status = self.mavsh_post_init()            
        print(self.status)
        #import pdb
        #pdb.set_trace()
        if status == mlink.MAVSH_ACTIVE:
            self.input_ready = True
            self.status = mlink.MAVSH_ACTIVE
        
        #try:
                #print(self.status)
        #except Exception:
            #print(Exception)

        # sanity check
        # should only be called when active         
        
        #self.mavsh_loop()
        import pdb
        #pdb.set_trace()
        loop = asyncio.get_event_loop()
        loop.create_task(self.mavsh_loop())
        loop.run_forever()
        
        
        """
        while self.state == mlink.ACTIVE:            
            if self.input_ready:
                cmd = get_input()
        """
    
    def stop(self):
        pass
    
    @property
    def input_ready(self):
        return self._input_ready
        
    @input_ready.setter
    def input_ready(self, b):
        """
        if b not in [False, True]:
            return
        else:
            self._input_ready = b
        """
        self._input_ready = b  
    
    
#gcs = MavshGCS('/dev/ttyACM0')
#gcs = MavshGCS('udp:0.0.0.0:8888')
#gcs = MavshGCS('udpout:0.0.0.0:8888')
#print(gcs)

m = MAVSH()
m.start()

#pprint(heartbeat)
#heartbeat = gcs.wait_heartbeat()
# i think we need to init inside the loop

#try:    
#    ht = Thread(target=gcs.heartbeat_loop, args=())
#    ht.start()    
#    gcs.mavsh_init()
#    gcs.message_loop()
    #print(status)
    #gcs.shell_loop(status)
#    gcs.loop.run_forever()
#except KeyboardInterrupt:
#    print(gcs.request_mavsh_shutdown())
=======

gcs = MavshGCS('/dev/ttyACM0')
print(gcs)
heartbeat = gcs.wait_heartbeat()
print(heartbeat)
# i think we need to init inside the loop
import sys

try:        
    gcs.loop.run_forever()

except KeyboardInterrupt:
    gcs.request_mavsh_shutdown()

"""
try:
    gcs.mavsh_init()
    gcs.message_loop()
"""
>>>>>>> main
