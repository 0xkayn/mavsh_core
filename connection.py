import sys
import time
import shlex
import serial
import asyncio
from pymavlink import mavutil
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
            raise Exception("Invalid session status. Must be MAVSH_INACTIVE or MAVSH_ACTIVE")        
        
        self._status = status
        

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
        # set these two to private so only the lib can change it
        self._system_id = 1 # systemid of the mav
        self._component_id = 191 # mlink.MAV_COMP_ID_ONBOARD_COMPUTER - not supported by ardupilotmega by default - I can edit the library enum to modify this 
        self.conn = mavutil.mavlink_connection(
            device=device, # assumes rpi
            source_system=self._system_id,
            source_component=self._component_id,
            baud=57600
        )
        self.mode = '' # not supported rn
        self._last_heartbeat_sent = 0    
        self.target_system = None
        self.target_component = None                    

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
            time.sleep(.5)
            synack = self.conn.recv_match(type='MAVSH_SYNACK', blocking=False)                    
            
            if synack:
                synack_recv = True            
        print(status)
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
            raise Exception("Session currently inactive")
        
        shutdown_status = mes.shutdown_flag
        # not sure if i want this up here yet or not
        if shutdown_status != mlink.MAVSH_SHUTDOWN:
            raise Exception("MAVSH SHUTDOWN exception..?")
        
        # ensure the shutdown is coming from the system we expect it to
        if self.target_system == mes.sys_id and self.target_component == mes.comp_id:
            self.send_mavsh_shutdown(mlink.MAVSH_EXITING)
            #self.status = mlink.MAVSH_INACTIVE
        
        # otherwise send a shutdown not allowed response
        else:
            self.send_mavsh_shutdown(mlink.MAVSH_SHUTDOWN_NOT_ALLOWED)

        return
    
    def handle_mavsh_init(self, mes):        
        # if the sysid of the sender is the same as the sysid of our gcs then we accept
        # need to check the connections dict of known connections for this 
        # temporarily evaulating to true 
        print(mes)
        # cant manually send a heartbeat directly to this component so...
        #if mes.sys_id == self.components['mav']['system_id']:
        if True:
            print(self.status)            

            # need to reply to the fc which should route the message, otherwise how will it get there..? 
            # ill likely need to modify the firmware again to actually have it forward/resend the message..?
            
            # accept the session only if the current session is inactive and the gcs sent an init flag
            if self.status == mlink.MAVSH_INACTIVE and mes.status_flag == mlink.MAVSH_INIT:
                self.target_system = mes.sys_id
                self.target_component = mes.comp_id
                # this is blocking, will have to consider changing this
                
                accepted = self.recv_synack(mes, mlink.MAVSH_ACCEPTED)
                print(mlink.MAVSH_ACCEPTED)
                # this should/will always evaluate to true
                if accepted == mlink.MAVSH_ACCEPTED:                    
                    self.status = mlink.MAVSH_ACTIVE
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
                    raise Exception("MAVSH_SESSION_EXISTS exception")
            
            # dont send a response unless one of those conditions are true
            else:
                pass
        
        # if we dont send heartbeats and wait for a moment at the start of a connection being established
        # this bool will definitely cause problems
        elif mes.sys_id != self.components['mav']['system_id']:
            # log this as an attempted mavsh session from a gcs that shouldnt be trying to establish it
            # need to add a logging function still
            self.send_ack(mlink.MAVSH_REJECTED)
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

            # if we recv
            elif mes_type == "MAVSH_ACK":                
                self.handle_mavsh_ack(mes)

            elif mes_type == "MAVSH_EXEC":
                #print(await self.loop.create_task(self.handle_mavsh_exec(mes)))
                #print( (await self.handle_mavsh_exec(mes)) )                
                #print(self.loop.create_task(self.run_cmd(mes.payload)))
                #print(self.handle_mavsh_exec(mes).decode)
                print(mes)

            # nor should we be getting responses                
            elif mes_type == "MAVSH_RESPONSE":
                print(mes)
            
            elif mes_type == "MAVSH_SYNACK":
                print(mes)
                self.send_synack()
                
                print("MAVSH SESSION ACCEPTED")
                time.sleep(.5)
                self.status = mlink.MAVSH_ACTIVE
                print(self.status)
                #print(mlink.MAVSH_ACTIVE)
            elif mes_type == "MAVSH_SHUTDOWN":
                print(mes)
                self.handle_mavsh_shutdown(mes)
            # populate our known components field when new components are found
            # only expecting to ever have 3
            elif mes_type == "HEARTBEAT":                
                #self.handle_heartbeat(mes)
                pass

            else:                
                pass

class MavshGCS(MavshComponent):

    def __init__(self, ip):
        super().__init__()
        self._system_id = 255 # systemid of the mav
        # need to set it as 1 for testing now
        self._component_id = 2 # 1 is assigned to the first gcs we connect with so we will use 2 to indicate its a different connection
        self.conn = mavutil.mavlink_connection(     
            device=ip, # assumed to be an IP when using crossfire AP, for testing itll be serial
            source_system=self._system_id,
            source_component=self._component_id,
            baud=57600 #this might be whats causing the issue 
        )
        self.mode = ''
        self.status = mlink.MAVSH_INACTIVE        
        self._last_heartbeat_sent = 0
        self.target_system = 1 # 1 is the systemid of the mav
        # 191 is the componentid of the companion computer - 191 is onboard controller in the MAV_COMPONENT enum 
        # sadly ardupilot doesnt use it - ill add it to custom firmware once 4.1 stable is out
        self.target_component = 191            
    
    # not sure if 2 mav_type gcs' will cause issues or not, might need to setup signing and have both have the key
    def send_heartbeats(self):
        now = time.time()
        if now - self._last_heartbeat_sent > 0.5:
            self._last_heartbeat_sent = now
            self.conn.mav.heartbeat_send(
                mlink.MAV_TYPE_GCS,
                mlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                0
            )

    def request_mavsh_shutdown(self):
        self.conn.mav.mavsh_shutdown_send(
            self._system_id,
            self._component_id,
            self.target_system,
            self.target_component,
            mlink.MAVSH_SHUTDOWN
        )
        return

    def handle_mavsh_ack(self, mes):
        
        if mes.status_flag == mlink.MAVSH_ACCEPTED:        
            # might need to make it active on the synack instead
            self.status = mlink.MAVSH_ACTIVE

            self.conn.mav.mavsh_synack_send(
                self._system_id,
                self._component_id,
                self.target_system,
                self.target_component
            )
            
            # since theres no way to guarantee message delivery in general I should probably also have the CC send a synack
            # if we recv it then we know the message was sent - 
            # im gonna have to write an FCS function wont I....
            # GG this is gonna mean modify the current packet validation structure
            
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
                self.send_mavsh_shutdown()
                
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
    
    def message_loop(self):

        
        while True:            
            self.send_heartbeats()                 
            
            mes = self.conn.recv_match(blocking=False)              
            while not mes:  
                mes = self.conn.recv_match(blocking=False)
            mes_type = mes.get_type()

            # a gcs shouldn't be getting an init
            if mes_type == "MAVSH_INIT":
                pass
            # if we get a mavsh_ack
            elif mes_type == "MAVSH_ACK":                
                self.handle_mavsh_ack(mes)
            
            # we shouldnt get a mavsh_exec
            elif mes_type == "MAVSH_EXEC":
                #print(await self.loop.create_task(self.handle_mavsh_exec(mes)))
                #print( (await self.handle_mavsh_exec(mes)) )                
                #print(self.loop.create_task(self.run_cmd(mes.payload)))
                #print(self.handle_mavsh_exec(mes).decode)
                print(mes)

            # handle the shell portion here
            elif mes_type == "MAVSH_RESPONSE":
                pass
            
            elif mes_type == "MAVSH_SYNACK":
                print(mes)

            elif mes_type == "MAVSH_SHUTDOWN":
                print(mes)

            elif mes_type == "HEARTBEAT":
                # need to remove prints from this later                 
                #self.handle_heartbeat(mes)
                pass                
                
            else:                
                #print(mes)
                pass