

class ModuleOptions:
    
    def __init__(self, options):
        self.options = options

class Setting:

    def __init__(self, name, type, default, description, value):
        self.name = name        
        self.type = type
        self.default = default
        self.description = ''
        self.value = value

    def set(self, value):
        if value == 'None' and self.default is None:
            value = None
        if value is not None:
            try:
                self.value = value
                return True
            except:
                return False


