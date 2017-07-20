"""Support master/server/client configurations"""

import os.path
import yaml

class BaseConigure(object):
    """Support basic YAML configuration file loading"""

    def __init__(self):
        self._config = None
        self.define_int_config_properties([
            ("registration_ttl", 300),
            ("reservation_ttl", 300),
        ])

    @staticmethod
    def exists(path):
        """check if a configuration file exists"""
        return os.path.isfile(path)

    def load(self, path):
        """load the configuration file"""
        with open(path) as stream:
            self._config = yaml.load(stream)

    @property
    def config(self):
        """ get the configuration dictionary data """
        return self._config

    def get_int_config(self, name, default_value):
        """ get integer value from the configuration with a default value """
        try:
            val = int(self._config[name]) if name in self._config.keys() else default_value
        except ValueError:
            val = default_value
        return val if val > 0 else default_value

    def define_int_config_properties(self, items):
        """ define an array of configuration based integer values with defaults """
        for item in items:
            name = item[0]
            def_value = item[1]
            setattr(type(self), name, property(\
                lambda self2, nam=name, defv=def_value: self2.get_int_config(nam, defv)))

# provide default values for unconfigured entries
class MasterConfigure(BaseConigure):
    """Support configuration for master node"""

    def __init__(self, path):
        """init with a given configuration file"""
        super(MasterConfigure, self).__init__()
        self.load(path)
        self.define_int_config_properties([
            ("port", 7878),
            ("default_server_request_count", 10),
        ])

# provide default values for unconfigured entries
class ServerConfigure(BaseConigure):
    """Support configuration for server node"""

    def __init__(self, path):
        """init with a given configuration file"""
        super(ServerConfigure, self).__init__()
        self.load(path)
        self.define_int_config_properties([
            ("port", 0),
            ("default_server_request_count", 10),
        ])

    @property
    def serverurl(self):
        """get the server listening url"""
        url = self._config['server-url'] if 'server-url' in self._config.keys()\
             else "clupy://localhost:{}"
        return url.format(self.port) # pylint: disable=E1101

