import sys
import shlex
from console.mavsh_module import *

class MavshConsole:
    
    def __init__(self, prompt="MAVSH> "):
        self._prompt = prompt
        self._modules = {}
        self._active_module = ''
        self.prompt = '> '
    
    @property
    def active_module(self):
        return self._active_module
    
    @active_module.setter
    def active_module(self, module):
        self._active_module = module        
        self.prompt = self._active_module.prompt

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, prompt):
        p = prompt.strip()
        self._prompt = f'{p} '     

    @property
    def modules(self):
        return self._modules

    def write(self, text):
        '''write to the console'''
        if isinstance(text, str):
            sys.stdout.write(text)
        else:
            sys.stdout.write(str(text))
        sys.stdout.flush()

    def writeln(self, text):
        '''write to the console with linefeed'''
        if not isinstance(text, str):
            text = str(text)
        self.write(text + '\n')

    def load_module(self, module):
        if isinstance(module, MavModule):
            if module.loaded == True:
                return
            else:
                self.modules[module.name] = module
                module.loaded = True
        else:
            return "cant load module"

    def main_loop(self):
        while True:
            cmd = input(self.prompt)
            try:
                main_cmd, module = cmd.split(' ',1)                                
            except:
                main_cmd = cmd.strip()

            if main_cmd.lower() == "load":
                self.load_module(module)

            elif main_cmd.lower() == "mavsh":
                self.active_module = self.modules['mavsh']
                continue

            if self.active_module:
                help_msg = self.active_module.commands
                vals = self.active_module.commands[0].options.values()
                if main_cmd.lower() == "help":
                    print(help_msg)
                elif main_cmd.lower() in vals:
                    from threading import Thread
                    Thread(target=vals[main_cmd.lower()], args=())