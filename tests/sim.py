from pymavlink import mavutil
from pymavlink.dialects.v20 import ardupilotmega as mavlink

# import dronekit's SITL module to setup our simulator
from dronekit_sitl import SITL

path = '/mnt/hdd/projects/quads/mavlink/Valkyrie/binaries/mavsh1'
sitl = SITL(path=path)
sitl.launch([], verbose=True, await_ready=True, restart=False)
sitl.block_until_ready(verbose=True) # explicitly wait until receiving commands
code = sitl.complete(verbose=True)


def wait_heartbeat(m):
    '''wait for a heartbeat so we know the target system IDs'''
    print("Waiting for APM heartbeat")
    msg = m.recv_match(type='HEARTBEAT', blocking=True)
    print("Heartbeat from APM (system %u component %u)" % (m.target_system, m.target_system))


# connect to the sitl instance and wait for the heartbeat msg to find its system ID
master = mavutil.mavlink_connection('tcp:localhost:5760')
wait_heartbeat(master)
'''
@vehicle.on_message('HEARTBEAT')
def listener(self, name, message):
    print(f'message: {message}')

@vehicle.on_message('RC_CHANNELS')
def rc_channel(self, name, message):
    pass

#@vehicle.on_message('PARAM_VALUE')
#def params(self, name, message):
#    pass
'''

@vehicle.on_message('*')
def other(self, name, message):
    print(f'message: {message}')

while True:
    continue



# Get some vehicle attributes (state)
#print("Get some vehicle attribute values:")
'''
print(f' GPS: {vehicle.gps_0}' \
      'Battery:{vehicle.battery}'\
      'Last Heartbeat: {vehicle.last_heartbeat}'\
      'Is Armable?: {vehicle.is_armable}'\
      'System status: { vehicle.system_status.state}'\
      'Mode: {vehicle.mode.name}'    # settable
      )

#Close vehicle object before exiting script
vehicle.close()

# Shut down simulator
sitl.stop()
print("Completed")
'''
