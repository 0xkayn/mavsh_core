
class MavshShutdownException(Exception):
    """Exception raised for mavsh shutdown errors.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="MAVSH_SHUTDOWN exception..?"):        
        self.message = message
        super().__init__(self.message)

class SessionStatusException(Exception):
    """Exception raised for mavsh session status errors.

    Attributes:
        message -- explanation of the error
    """
    
    def __init__(self, message="SESSION_STATUS exception..?"):        
        self.message = message
        super().__init__(self.message)

class SessionExistsException(Exception):
    """Exception raised for mavsh session status errors.

    Attributes:
        message -- explanation of the error
    """
    
    def __init__(self, message="MAVSH_SESSION_EXISTS"):        
        self.message = message
        super().__init__(self.message)