class ModuleCommand:

    def __init__(self, name, options, description="change me"):
        self._name = name
        self._options = options
        self._description = description        
    
    def __repr__(self):
        return f'{self.name}\n {self.options}' 

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        if isinstance(description, str):
            self._description = description
        else:
            return "some error"
        
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if isinstance(name, str):
            self._name = name
        else:
            return "some error"

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, option):
        if isinstance(options, dict):
            self._options = options
        else:
            return "some error"
            
class MavModule:
    
    def __init__(self, name, prompt, description):
        self._name = name             
        self._active = False
        self._loaded = False
        self._prompt = prompt
        self._description = description
        self._settings = []
        self._commands = []

    @property
    def commands(self):
        return self._commands

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        if isinstance(name, str):
            self._name = name
        else:
            return "some error"

    @property
    def loaded(self):
        return self._loaded
    
    @loaded.setter
    def loaded(self, b):
        if isinstance(b, bool):
            self._loaded = b
        else:
            return "some error"

    @property
    def active(self):
        return self.active
    
    @active.setter
    def active(self, b):
        if isinstance(b, bool):
            self._active = b
        else:
            return "some error"

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, prompt):
        p = prompt.strip()
        self._prompt = f'{p} '            

    def add_setting(self, s):
        if isinstance(s, Setting):
            self._settings.append(s)
        else:
            return
    
    def add_command(self, c):
        if isinstance(c, ModuleCommand):
            self._commands.append(c)
        else:
            return
            