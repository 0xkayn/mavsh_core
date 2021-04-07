#print "Start simulator (SITL)"

import dronekit_sitl
sitl = dronekit_sitl.start_default()
connection_string = sitl.connection_string()
# Import DroneKit-Python

from dronekit import connect, VehicleMode
# Connect to the Vehicle.
print("Connecting to vehicle on:  %s" % (connection_string,))
vehicle = connect(connection_string, wait_ready=True)

# Get some vehicle attributes (state)
print("Get some vehicle attribute values:")
print(f' GPS: {vehicle.gps_0}' \
      'Battery:{vehicle.battery}'\
      'Last Heartbeat: {vehicle.last_heartbeat}'\
      'Is Armable?: {vehicle.is_armable}'\
      'System status: { vehicle.system_status.state}'\
      'Mode: {vehicle.mode.name}'    # settable
      )


# Close vehicle object before exiting script
vehicle.close()

# Shut down simulator
sitl.stop()
print("Completed")

