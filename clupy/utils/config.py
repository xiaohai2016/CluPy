"""Support master/server/client configurations"""

import os.path
import yaml

class BaseConigure(object):
    """Support basic YAML configuration file loading"""

    def __init__(self):
        self._config = None

    @staticmethod
    def exists(path):
        """check if a configuration file exists"""
        return os.path.isfile(path)

    def load(self, path):
        """load the configuration file"""
        with open(path) as stream:
            self._config = yaml.load(stream)

# provide default values for unconfigured entries
class MasterConfigure(BaseConigure):
    """Support configuration for master node"""

    def __init__(self, path):
        """init with a given configuration file"""
        super(MasterConfigure, self).__init__()
        self.load(path)

    @property
    def port(self):
        """get the master node listening port"""
        try:
            port = int(self._config['port'])
        except ValueError:
            port = 7878
        return port

# provide default values for unconfigured entries
class ServerConfigure(BaseConigure):
    """Support configuration for server node"""

    def __init__(self, path):
        """init with a given configuration file"""
        super(ServerConfigure, self).__init__()
        self.load(path)

    @property
    def port(self):
        """get the server node listening port"""
        try:
            port = int(self._config['port'])
        except ValueError:
            port = 7877
        return port
