
"""
Generate a message using different MAVLink versions, put in a buffer and then read from it.
"""

from __future__ import print_function
from builtins import object

from pymavlink.dialects.v20 import ardupilotmega as mavlink
from pymavlink import mavutil

class fifo(object):
    def __init__(self):
        self.buf = []
    def write(self, data):
        self.buf += data
        return len(data)
    def read(self):
        return self.buf.pop(0)


def test_protocol(mavlink, signing=False):
    # we will use a fifo as an encode/decode buffer
    f = fifo()

    print("Creating MAVLink message...")
    # create a mavlink instance, which will do IO on file object 'f'
    mav = mavlink.MAVLink(f)
    
    if signing:
        mav.signing.secret_key = bytearray(chr(42)*32, 'utf-8' )
        mav.signing.link_id = 0
        mav.signing.timestamp = 0
        mav.signing.sign_outgoing = True

    m = mavlink.MAVLink_mavsh_init_message(255, 1,1,200,0)
    print(mav.mavsh_init_encode(255, 1,1,200,0))
    #print(mav.mavsh_response_encode(255, 1,1,200,0))
    
    # set the WP_RADIUS parameter on the MAV at the end of the link
    #mav.param_set_send(7, 1, b"WP_RADIUS", 101, mavlink.MAV_PARAM_TYPE_REAL32)
    
    #m = mavlink.MAVLink_mavsh_init_message(1, 1)
    m = mavlink.MAVLink_mavsh_init_message(255, 1,1,200,0)
        
    #mav.send()
    
    #MAVLink_mavsh_init_message()
    # alternatively, produce a MAVLink_param_set object 
    # this can be sent via your own transport if you like
    #m =
    #m = mav.param_set_encode(7, 1, b"WP_RADIUS", 101, mavlink.MAV_PARAM_TYPE_REAL32)


    m.pack(mav)

    # get the encoded message as a buffer
    b = m.get_msgbuf()

    bi=[]
    for c in b:
        bi.append(int(c))
    print("Buffer containing the encoded message:")
    print(bi)

    print("Decoding message...")
    # decode an incoming message
    m2 = mav.decode(b)

    # show what fields it has
    print("Got a message with id %u and fields %s" % (m2.get_msgId(), m2.get_fieldnames()))

    # print out the fields
    print(m2)


print("\nTesting mavlink2\n")
test_protocol(mavlink)

print("\nTesting mavlink2 with signing\n")
test_protocol(mavlink, True)

print('testing random message?')
#print(mavlink.MAVLink_mavsh_init_message(1,1))

#print(mavsh_init_send(target_system=1, setup_flag=mavlink.MAVSH_SESSION_INIT ))
