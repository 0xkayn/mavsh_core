from pymavlink import mavutil
from dronekit import connect

# Connect to the Vehicle using dronekit "connection string" (in this case an address on network)
#vehicle = connect('udp:0.0.0.0:14550')
vehicle = connect('/dev/ttyS0', wait_ready=True, baud=57600, source_system=1, source_component=191)

# Wait for the first heartbeat 
# This sets the system and component ID of remote system for the link

#Create a message listener for all messages.
"""
@vehicle.on_message('MAVSH_INIT')
def listener(self, name, message):
    print(f'message: {message}')


@vehicle.on_message('RC_CHANNELS')
def rc_channel(self, name, message):
    pass

@vehicle.on_message('PARAM_VALUE')
def params(self, name, message):
    pass
"""

@vehicle.on_message('MAVSH_INIT')
def other(self, name, message):
    print(f'message: {message}')

@vehicle.on_message('HEARTBEAT')
def hb(self, name, message):
    print(f'message: {message}')

@vehicle.on_message('MAVSH_ACK')
def ack(self, name, message):
    print(f'message: {message}')

@vehicle.on_message('MAVSH_EXEC')
def exec(self, name, message):
    print(f'message: {message}')


@vehicle.on_message('MAVSH_RESPONSE')
def other(self, name, message):
    print(f'message: {message}')


while True:
    continue


    
