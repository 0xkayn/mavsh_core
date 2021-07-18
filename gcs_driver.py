from connection import *          
from threading import Thread

#gcs = MavshGCS('/dev/ttyACM0')
gcs = MavshGCS('udp:0.0.0.0:8888')
#gcs = MavshGCS('udpout:0.0.0.0:8888')
print(gcs)

#pprint(heartbeat)
#heartbeat = gcs.wait_heartbeat()
# i think we need to init inside the loop
try:
    #gcs.send_heartbeats()
    ht = Thread(target=gcs.heartbeat_loop, args=())
    ht.start()
    #print(heartbeat)
    gcs.mavsh_init()
    status = gcs.message_loop()
    print(status)
    gcs.shell_loop(status)
    #gcs.loop.run_forever()
except KeyboardInterrupt:
    print(gcs.request_mavsh_shutdown())


