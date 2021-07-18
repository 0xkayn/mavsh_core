import sys
import time
import shlex
import serial
import asyncio
from queue import Queue
from threading import Thread
from pymavlink import mavutil
from mavsh_exceptions import *
from asyncio.subprocess import PIPE, STDOUT
from pymavlink.dialects.v20 import ardupilotmega as mlink

# come up with a way for a latency-based wait time - this will only work with field testing
# integrate this into mavproxy later
class MavshComponent:
    
    def __init__(self):
 
        self._status = mlink.MAVSH_INACTIVE                   
        #only will support this for now
        self.modes = {
            mlink.MAV_TYPE_GCS:'interactive',
            mlink.MAV_TYPE_ONBOARD_CONTROLLER:'background'
        }
        self._known_components = {}
        self._system_id = -1
        self._component_id = -1
        self._is_sending_heartbeats = False
        self.conn = None

    @property
    def sysid(self):
        return self._system_id

    @property
    def compid(self):
        return self._component_id

    @property 
    def components(self):
        return self._known_components

    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, status):
        if status not in [mlink.MAVSH_INACTIVE, mlink.MAVSH_ACTIVE]:
            raise SessionStatusException("Invalid session status. Must be MAVSH_INACTIVE or MAVSH_ACTIVE")        
        
        self._status = status       
    
    @property
    def is_sending_heartbeats(self):
        return self._is_sending_heartbeats
    
    @is_sending_heartbeats.setter
    def is_sending_heartbeats(self, val):
        if type(val) != bool:
            return "some error"
        else:
            self._is_sending_heartbeats = val

    def __repr__(self):
        if self.conn is not None:
            return f'sysid: {self.sysid}\n' \
            f'compid: {self.compid}\n' \
            f'known components: {self.components}\n' 
        else:
            return 'No connection established'

    def handle_heartbeat(self, mes):    
        """
        populates self._known_components with a new system when one of three systems are encountered
        """         
        src_system = mes.get_srcSystem()
        src_component = mes.get_srcComponent()

        # if the tuple isnt in our known components tuple then we associate it with the component it is
        if (src_system, src_component) not in self._known_components.values():
            
            if mes.type == mlink.MAV_TYPE_ONBOARD_CONTROLLER:
                self._known_components['companion'] = {'system_id':src_system, 'component_id':src_component}                
            
            # only supporting these for now because I fly a quad
            elif mes.type == mlink.MAV_TYPE_QUADROTOR: # 2 
                self._known_components['mav'] = {'system_id':src_system, 'component_id':src_component}                            
            
            elif mes.type == mlink.MAV_TYPE_GCS: # 
                self._known_components['gcs'] = {'system_id':src_system, 'component_id':src_component}

        return
    
    def wait_heartbeat(self, blocking=True, timeout=None):
        """
        wait for a heartbeat so we know the target system IDs
        sets: self.conn.target_system & self.conn.target_component
        """
        return self.conn.recv_match(type='HEARTBEAT', blocking=blocking, timeout=timeout)

    def wait_mavsh_ack(self, blocking=True, timeout=None):
        """ wait for MAVSH_ACK to initialize the shell """
        return self.conn.recv_match(type='MAVSH_ACK', blocking=blocking, timeout=timeout)

    def wait_mavsh_synack(self, blocking=True, timeout=1):
        """ wait for MAVSH_SYNACK """
        return self.conn.recv_match(type='MAVSH_SYNACK', blocking=blocking, timeout=timeout)

class MavshCompanion(MavshComponent):

    def __init__(self, device):
        super().__init__()        
        self._system_id = 1 # systemid of the mav
        self._component_id = 191 
        # mlink.MAV_COMP_ID_ONBOARD_COMPUTER 
        # not supported by ardupilotmega by default, will have to edit the library enum to have it 
        self.conn = mavutil.mavlink_connection(
            device=device, # assumes rpi
            source_system=self._system_id,
            source_component=self._component_id,
            baud=921600
            #baud=115200
            
           # baud=57600
        )

        self.mode = '' # not supported rn
        self._last_heartbeat_sent = 0    
        self.target_system = None
        self.target_component = None          
        self.loop = asyncio.get_event_loop()

    def send_heartbeat(self):
        self.conn.mav.heartbeat_send(
            mlink.MAV_TYPE_ONBOARD_CONTROLLER,
            mlink.MAV_AUTOPILOT_INVALID,
            0,
            0,
            0
        )
        return 
    
    def send_heartbeats(self):
        """
        need some way to check where this is being called from. If outside of the lib/drivers then
        we need to 
        """
        now = time.time()
        if now - self._last_heartbeat_sent > 0.5:
            self._last_heartbeat_sent = now
            self.send_heartbeat()

        return
    
    def send_ack(self, mes, status):
        self.conn.mav.mavsh_ack_send(
            self._system_id,
            self._component_id,
            mes.sys_id,
            mes.comp_id,
            status
        )
        return

    def send_synack(self):                       
        self.conn.mav.mavsh_synack_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component
        )        
        return
    
    def recv_synack(self, mes, status):
        """ Send a MAVSH_ACK and wait for a MAVSH_SYNACK """
        synack_recv = False
        
        while not synack_recv:
            self.send_ack(mes, status)                        
            synack = self.conn.recv_match(type='MAVSH_SYNACK', blocking=False)                    
            time.sleep(.5)
            if synack:
                synack_recv = True

        return status
    
    def send_mavsh_shutdown(self, status):
        self.conn.mav.mavsh_shutdown_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component,
            status
        )
        return

    def handle_mavsh_shutdown(self, mes):
        
        if self.status == mlink.MAVSH_INACTIVE:
            raise SessionStatusException("Session currently inactive")
        
        shutdown_status = mes.shutdown_flag
        # not sure if i want this up here yet or not
        if shutdown_status != mlink.MAVSH_SHUTDOWN:
            raise MavshShutdownException("MAVSH SHUTDOWN exception..?")
        
        # ensure the shutdown is coming from the system we expect it to
        if self.target_system == mes.sys_id and self.target_component == mes.comp_id:
            self.send_mavsh_shutdown(mlink.MAVSH_EXITING)
            self.status = mlink.MAVSH_INACTIVE
        
        # otherwise send a shutdown not allowed response
        else:
            self.send_mavsh_shutdown(mlink.MAVSH_SHUTDOWN_NOT_ALLOWED)

        return
    
    def handle_mavsh_init(self, mes):                
        # need to check the connections dict of known connections for this
        print(mes)
        """
        #if the sysid and compid of the sender is the same as the sysid of our gcs then we accept
        if mes.sys_id == self.components['gcs']['system_id'] and mes.comp_id == self.components['gcs']['component_id']
        
        #alternatively I could check
        if {'system_id':mes.sys_id, 'component_id': mes.comp_id} in self.components.values():
        
        #which would allow the messages to be recvd from a companion as well or a 2nd gcs..?
        """        
        #if {'system_id':mes.sys_id, 'component_id': mes.comp_id} in self.components.values():            
        if True:
            # accept the session only if the current session is inactive and the gcs sent an init flag
            if True:
            #if self.status == mlink.MAVSH_INACTIVE and mes.status_flag == mlink.MAVSH_INIT:
            #if mes.status_flag == mlink.MAVSH_INIT:
                self.target_system = mes.sys_id
                self.target_component = mes.comp_id
                accepted = self.recv_synack(mes, mlink.MAVSH_ACCEPTED)                
                
                # this should/will always evaluate to true
                if accepted == mlink.MAVSH_ACCEPTED:                    
                    #self.status = mlink.MAVSH_ACTIVE
                    return mlink.MAVSH_ACCEPTED
                else:
                    raise Exception("MAVSH_ACCEPTED exception")
            
            # let the user know a session already exists
            elif self.status == mlink.MAVSH_ACTIVE:
                print('already active')
                # print to the console after i create it
                # need to check for a synack here as well but to change later in case
                exists = self.send_ack(mes, mlink.MAVSH_SESSION_EXISTS)                    
                
                # should always be true
                if exists == mlink.MAVSH_SESSION_EXISTS:
                    return mlink.MAVSH_SESSION_EXISTS
                else:
                    raise SessionExistsException("MAVSH_SESSION_EXISTS exception")
            
            # dont send a response unless one of those conditions are true
            else:
                pass
        
        # if we dont send heartbeats and wait for a moment at the start of a connection being established
        # this bool will definitely cause problems
        elif mes.sys_id != self.components['mav']['system_id']:
            """
             log this as an attempted mavsh session from a gcs that shouldnt be trying to establish it
             need to add a logging function still
             """
            self.send_ack(mes, mlink.MAVSH_REJECTED)
            return mlink.MAVSH_REJECTED
        # no response otherwise
        else:
            return

    def message_loop(self):    
        
        while True:
            self.send_heartbeats()
            mes = self.conn.recv_match(blocking=False)              
            while not mes:
                mes = self.conn.recv_match(blocking=False)
            
            mes_type = mes.get_type()
            
            # theres a chance the gcs might miss this message so we should send the message a few times            
            if mes_type == "MAVSH_INIT":                
                self.handle_mavsh_init(mes)
                print(mes)
            # if we recv
            elif mes_type == "MAVSH_ACK":                
                self.handle_mavsh_ack(mes)
                print(mes)
            elif mes_type == "MAVSH_SYNACK":
                print(mes)
                for i in range(3):
                    self.send_synack()
                    time.sleep(1)
                
                print("MAVSH SESSION ACCEPTED")
                self.status = mlink.MAVSH_ACTIVE
                self.loop.create_task(self.shell_loop())
                return mlink.MAVSH_ACTIVE
                
            elif mes_type == "MAVSH_SHUTDOWN":                
                self.handle_mavsh_shutdown(mes)
                print(mes)
            
            elif mes_type == "HEARTBEAT":                                
                """
                populate our known components field when new components are found
                only expecting to ever have 3
                """                            
                self.handle_heartbeat(mes)                
                print(mes)
            else:             
                pass
    
    def send_mavsh_response(self, status, chunk):
        
        self.conn.mav.mavsh_response_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component,
            status, # cmd_status mlink.complete
            bytes(chunk)
            #chunk
        )
        return

    async def handle_mavsh_exec(self, mes):         
        response_queue = Queue()

        def chunk_result(res, q):
            # chunks the response message into a max size of 154 bytes          
            #return [res[i:i+154] for i in range(0, len(res), 154)]
            for i in range(0, len(res), 153):                        
                q.put(res[i:i+153])

        async def run_cmd(cmd):
            # shlex.split will escape characters used for cmd injection
            # but create_subprocess_shell requires a string so we join the list
            cmd = " ".join(shlex.split(cmd))
            p = await asyncio.create_subprocess_shell(cmd,
                stdin=PIPE, 
                stdout=PIPE, 
                stderr=STDOUT
            )
            
            """
            #command_started = time.time()
            
            #now = time.time()
            #if now - command_started > .5:
            #    self.send_mavsh_response(mlink.MAVSH_EXECUTING, '')
                

                
                ideally will have a different status flag for this situation to know data 
                isn't ready to send                
                _____________________________________________________________________________
                
                one mod to make is: change cmd_status enum to cmd_flags contain:
                MAVSH_COMMAND_IDLE
                MAVSH_COMMAND_TRANSMITTING (for when were sending info but cmd not complete?)
                MAVSH_COMMAND_EXECUTING (there need to be more most likely)
                MAVSH_COMMAND_COMPLETE
                _____________________________________________________________________________
                this will let me handle the connection lib better
                """
            #import pdb
            #pdb.set_trace()
            return (await p.communicate())[0]
        
        command_started = time.time()
        result = await run_cmd(mes.payload)

        # send a response message every 2 seconds to let us know if the command has finished
        # this will be particularly useful when showing when a command/scan completes on my OSD        
        print(result)

        if len(result) > 154:                        
            chunk_result(result, response_queue)
        else:
            response_queue.put(result)
        
        
        while not response_queue.empty():
            """
            need to modify this to let us know when the final chunk is being sent/when full packet ends 
            """
            try:
                chunk = response_queue.get()                
                if response_queue.qsize() != 0:
                    """
                    once cmd_status enum changes set this to MAVSH_COMMAND_COMPLETE
                    """
                    self.send_mavsh_response(mlink.MAVSH_EXECUTING, chunk)                    
                elif response_queue.qsize == 0:
                    self.send_mavsh_response(mlink.MAVSH_IDLE, chunk)
                    # this MIGHT be causing the connection loss issue

            except Empty:
                import pdb
                pdb.set_trace()
                #self.send_mavsh_response(mlink.MAVSH_EXECUTING, '')
                #self.send_heartbeat()


        return result

    async def shell_loop(self):                       
        
        while True:
            self.send_heartbeats()
            
            mes = self.conn.recv_match(blocking=False)              
            while not mes:  
                mes = self.conn.recv_match(blocking=False)
            mes_type = mes.get_type()
                        
            if mes_type == "MAVSH_EXEC":
                await self.handle_mavsh_exec(mes)
            elif mes_type == "MAVSH_RESPONSE":
                pass                                    
            elif mes_type == "MAVSH_SHUTDOWN":
                """
                when we recv this we need some way to escape out of this loop, maybe threading?
                """
                print(mes)
                
            else:                
                pass

class MavshGCS(MavshComponent):

    def __init__(self, ip):
        super().__init__()
        self._system_id = 255 # systemid of the gcs
        # need to set it as 1 for testing now
        self._component_id = 1 # 1 is assigned to the first gcs we connect with so we will use 2 to indicate its a different connection
        self.conn = mavutil.mavlink_connection(
            device=ip, # assumed to be an IP when using crossfire AP, for testing itll be serial
            source_system=self._system_id,
            source_component=self._component_id
            #baud=57600
        )
        self.mode = ''
        self.status = mlink.MAVSH_INACTIVE
        self._last_heartbeat_sent = 0        
        self.target_system = 1 # 1 is the systemid of the mav
        #self.target_system = 51 #  temporary
        #191 is the componentid of the companion computer - 191 is onboard controller in the MAV_COMPONENT enum 
        # sadly ardupilot doesnt use it - ill add it to custom firmware once 4.1 stable is out
        self.target_component = 191
        #self.target_component = 68 # temporary
        self.loop = asyncio.get_event_loop()
    
    def send_heartbeat(self):
        self.conn.mav.heartbeat_send(
            mlink.MAV_TYPE_GCS,
            mlink.MAV_AUTOPILOT_INVALID,
            0,
            0,
            0
        )
        return

    # not sure if 2 mav_type gcs' will cause issues or not, might need to setup signing and have both have the key
    def send_heartbeats(self):
        now = time.time()
        if now - self._last_heartbeat_sent > 0.5:
            self._last_heartbeat_sent = now
            self.send_heartbeat()
    
        return

    def send_synack(self):
        self.conn.mav.mavsh_synack_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component
        )
        return
    
    def recv_synack(self):
        """ Send a MAVSH_SYNACK and wait for a MAVSH_SYNACK """        
        synack = self.conn.recv_match(type='MAVSH_SYNACK', blocking=False,timeout=None)
        while not synack:
            self.send_synack()            
            synack = self.conn.recv_match(type='MAVSH_SYNACK', blocking=False)                                
            if synack:                
                return synack

            time.sleep(.5)
        
        return synack   

    def send_mavsh_shutdown(self, status):
        self.conn.mav.mavsh_shutdown_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component,
            status
        )
        return                            
    
    def request_mavsh_shutdown(self):
        self.send_mavsh_shutdown(mlink.MAVSH_SHUTDOWN)
        return

    def send_mavsh_exec(self, status, cmd):        
        self.conn.mav.mavsh_exec_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component,
            status,
            cmd.encode()
        )
        return
        
    def send_mavsh_init(self):
        self.conn.mav.mavsh_init_send(            
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component,
            mlink.MAVSH_INIT
        )
        return
    
    def mavsh_init(self):        
        """ MAVSH init procedure """
        
        ack_msg = self.conn.recv_match(type='MAVSH_ACK', blocking=False,timeout=None)        
        
        while not ack_msg:            
            self.send_mavsh_init()            
            ack_msg = self.conn.recv_match(type='MAVSH_ACK', blocking=False,timeout=None)
            time.sleep(.5) # the location of these sleeps is causing issues
            # really need to setup a good retransmission mechanism
        
        self.handle_mavsh_ack(ack_msg)                

        return ack_msg.status_flag

    def handle_mavsh_ack(self, mes):
        
        if mes.status_flag == mlink.MAVSH_ACCEPTED:
            """
            since theres no way to guarantee message delivery in general I should probably also have the CC send a synack
            if we recv it then we know the message was sent - 
            im gonna have to write an FCS function wont I....
            GG this is gonna mean modify the current packet validation structure
            """
            synack = self.recv_synack()            
            return mlink.MAVSH_ACCEPTED

        elif mes.status_flag == mlink.MAVSH_REJECTED:
            # not sure rn - only occurs w/invalid gcs/sysid combos
            print('session rejected??')
            return mlink.MAVSH_REJECTED

        elif mes.status_flag == mlink.MAVSH_SESSION_EXISTS:
            print('session exists')
            # if a session exists already but not with us then something is wrong...
            # im gonna guess its bc i havent setup a way to teardown the session yet
            if self.status != mlink.MAVSH_ACTIVE:
                # try to send a mavsh shutdown packet here
                # should only accept the shutdown packet from the connection which set it up - use sysid/compid for this
                self.request_mavsh_shutdown()                
                # wait 15 s for a shutdown packet - might need to make this None depending on how latency is outside
                shutdown_msg = self.conn.recv_match(type='MAVSH_SHUTDOWN', blocking=True, timeout=15)                
                #shutdown is accepted
                if shutdown_msg.shutdown_flag == mlink.MAVSH_EXITING:                
                    self.status = mlink.MAVSH_INACTIVE
                    # self.console.kill or something like this

                # if its not accepted then someone must have another session open...
                elif shutdown_msg.shutdown_flag == mlink.MAVSH_SHUTDOWN_NOT_ALLOWED:
                    pass
                    # this is the actual sus part...

    def message_loop(self):

        while self.status != mlink.MAVSH_ACTIVE:   
        #while True:
            self.send_heartbeats()                 

            mes = self.conn.recv_match(blocking=False)              
            while not mes:
                mes = self.conn.recv_match(blocking=False)
            mes_type = mes.get_type()

            if mes_type == "MAVSH_ACK":                
                self.handle_mavsh_ack(mes)            
            
            elif mes_type == "MAVSH_SYNACK":
                print(mes)
                if self.status == mlink.MAVSH_INACTIVE:
                    self.status = mlink.MAVSH_ACTIVE                
                    #self.loop.create_task(self.shell_loop(self.status))
                    return self.status
            
            elif mes_type == "MAVSH_SHUTDOWN":
                print(mes)

            elif mes_type == "HEARTBEAT":                
                self.handle_heartbeat(mes)
                pass                

            else:                                
                pass
    
    def heartbeat_loop(self):
        while True:
            self.send_heartbeats()    
    """

    Two variations of handling response mes, need to change enum flags first
    
    def handle_mavsh_response(self, mes, q):                
        # check to see if we will be recv more messages
        if mes.cmd_status == mlink.MAVSH_IDLE:
            out = mes.response
            while not q.empty():
                try:
                    out += q.get()
                except Empty:
                    return out

        elif mes.cmd_status == mlink.MAVSH_EXECUTING:
            q.put(mes.response)
            return mes.cmd_status
                    

    def handle_mavsh_resq(self, mes, q):                
        if mes.cmd_status == mlink.MAVSH_EXECUTING:
            res += mes.response
            mes_q.put(mes.response)
            input_ready = False

        elif mes.cmd_status == mlink.MAVSH_IDLE:
            res += mes.response
            print(res)
            out = mes.response
            while not mes_q.empty():
                try:
                    print(mes_q.get())
                except Empty:
                    print(out)
                    input_ready = True  
       """ 


    def shell_loop(self, status):
        
        #ht = Thread(target=self.heartbeat_loop, args=() )        
        #ht.start()        
        res = ""
        input_ready = True        
        
        while True:        
            #self.send_heartbeats()
            if input_ready == True:
                inp = input("MAVSH> ")
                cmd = " ".join(shlex.split(inp))
                self.send_mavsh_exec(status, cmd)

            """
            mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=True)            
            print(mes)
            # adding this block to search for more responses until idle flag is found
            if mes.cmd_status == mlink.MAVSH_EXECUTING:
                while mes.cmd_status != mlink.MAVSH_IDLE:
                    print(mes)
                    r = mes.response.strip()
                    print(r)                
                    mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=True)            
                
            """

            response_queue = Queue()
            while True:
                #mes = self.conn.recv_match(type="MAVSH_RESPONSE", condition="MAVSH_RESPONSE.cmd_status!=0", blocking=False)            
                #while not mes:
                #    
                mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=False)
                while not mes:
                    mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=False)

                response_queue.put(mes)
                print(mes) 
                if mes.cmd_status == mlink.MAVSH_IDLE:
                    #response_queue.put(mes)    
                    #                                     
                    break
                import pdb
                pdb.set_trace()
            
            """
            #mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=False)
            input_ready = False
            mes = self.conn.recv_match(blocking=False)            
            while not mes:
                mes = self.conn.recv_match(blocking=False)
                            
            mes_type = mes.get_type()
            
            
            if mes_type == "MAVSH_RESPONSE":                   
                import pdb
                pdb.set_trace()
                r = mes.response.strip()                
                if mes.cmd_status == mlink.MAVSH_EXECUTING:                    
                    res += mes.response
                    #print(r)
                    #mes_q.put(mes.response)                    
                    input_ready = False

                elif mes.cmd_status == mlink.MAVSH_IDLE:
                    res += mes.response
                    print(res)
                    #print(self.conn.messages)
                    #import pdb
                    #pdb.set_trace()
                    #print(r)
                    res = ""
                    input_ready = True  
            
            elif mes_type == "MAVSH_SHUTDOWN":
                print(mes)
        """
        

    async def shelll_loop(self, status):
            
        res = ""
        input_ready = True        
        
        while True:                
            
            if input_ready == True:
                inp = input("MAVSH> ")
                cmd = " ".join(shlex.split(inp))
                self.send_mavsh_exec(status, cmd)
            
            mes = self.conn.recv_match(blocking=False)   
            while not mes:  
                mes = self.conn.recv_match(blocking=False)         
            mes_type = mes.get_type()
                        
            if mes_type == "MAVSH_RESPONSE":
                await print(mes)
                await response_queue.put(mes)
                
                #if mes.cmd_status == mlink.MAVSH_IDLE:                
                #print(mes)
            """
            #mes = self.conn.recv_match(type="MAVSH_RESPONSE", blocking=False)
            input_ready = False
            mes = self.conn.recv_match(blocking=False)            
            while not mes:
                mes = self.conn.recv_match(blocking=False)
                            
            mes_type = mes.get_type()
            
            
            if mes_type == "MAVSH_RESPONSE":                   
                import pdb
                pdb.set_trace()
                r = mes.response.strip()                
                if mes.cmd_status == mlink.MAVSH_EXECUTING:                    
                    res += mes.response
                    #print(r)
                    #mes_q.put(mes.response)                    
                    input_ready = False

                elif mes.cmd_status == mlink.MAVSH_IDLE:
                    res += mes.response
                    print(res)
                    #print(self.conn.messages)
                    #import pdb
                    #pdb.set_trace()
                    #print(r)
                    res = ""
                    input_ready = True  
            
            elif mes_type == "MAVSH_SHUTDOWN":
                print(mes)
        """