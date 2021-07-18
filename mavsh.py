from console.mavsh_module import ModuleCommand, MavModule
from console.mavsh_console import MavshConsole
from connection import *

class MavshModule(MavModule):

    def __init__(self, name, prompt, description):
        super().__init__(name, prompt, description)
        self.name = name
        self.prompt = prompt
        self.description = description        
        self.add_command(ModuleCommand('mavsh', {
            'connect': self.conn,
            'init': self.minit,
            'exec': self.exec
            })
        )        
        
    def conn(self):
        gcs = MavshGCS('/dev/ttyACM0')
        heartbeat = gcs.wait_heartbeat()

    def minit(self):
        gcs.mavsh_init()
        
    def exec(self):
        status = gcs.message_loop()        
        gcs.shell_loop(status)
    
    def add_command(self, c):
        if isinstance(c, ModuleCommand):
            self.commands.append(c)
        else:
            pass
                

#except KeyboardInterrupt:
#    print(gcs.request_mavsh_shutdown())


c = MavshConsole()
m = MavshModule('mavsh', 'MAVSH> ', 'mavsh control module')   
c.load_module(m)
c.main_loop()