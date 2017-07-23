""" server side remote execution support """
from __future__ import print_function
import logging
import pickle
import base64
import inspect
import tornado.web
from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPError

class ServerExecutionServiceSingleton(object):
    """ the singleton class for ServerExecutionService """

    instance = None

    def __new__(cls, config):
        """ service instance creation """
        if not ServerExecutionServiceSingleton.instance:
            ServerExecutionServiceSingleton.instance = \
                ServerExecutionServiceSingleton.ServerExecutionService(config)
        return ServerExecutionServiceSingleton.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, val):
        return setattr(self.instance, name, val)

    class ServerExecutionService(object):
        """ the management class for server node registrations with the master nodes """

        def __init__(self, config):
            self._config = config
            self._logger = logging.getLogger("server")

        def create_sand_box(self, client_id, execution_id):
            """ to create a sand box execution environment for client """
            self._logger.info("to create sandbox for (%s), execution (%s)", client_id, execution_id)
            return client_id + "_" + execution_id

        def get_module_import_name(self, file_name):
            """ based on the script file uploading implementation and sandbox
                organization, return a module name for importing
                The current hack is simply return the file name part
            """
            module_name = file_name[file_name.rfind('/')+1:]
            module_name = module_name[:module_name.rfind('.')]
            return module_name

        def execute_code(self, sandbox_id, file_name, func_name, input_data):
            """ execute specified function with the given input_datq """
            self._logger.info("excute: %s:%s", file_name, func_name)
            module_name = self.get_module_import_name(file_name)
            module = __import__(module_name)
            func = getattr(module, func_name)
            argspec = inspect.getargspec(func)
            all_args = []
            if argspec.args:
                for arg in argspec.args:
                    all_args.append(input_data[arg])
            if argspec.varargs:
                for arg in argspec.varargs:
                    all_args.append(input_data[arg])
            all_kwargs = {}
            if argspec.keywords:
                for arg in argspec.keywords:
                    all_kwargs[arg] = input_data[arg]
            return func(*all_args, **all_kwargs)

class CreateSandboxHandler(tornado.web.RequestHandler):
    """ handler for create sand box """

    def initialize(self, config=None):
        """ handler initialization, called for each request """
        self._config = config # pylint: disable=W0201

    def get(self, client_id, execution_id):
        """ the routine for creating sandbox and return the id """
        execution_service = ServerExecutionServiceSingleton(self._config)
        self.write(execution_service.create_sand_box(client_id, execution_id))

class ExecuteFunctionHandler(tornado.web.RequestHandler):
    """ handler for remote function execution """

    def initialize(self, config=None):
        """ handler initialization, called for each request """
        self._config = config # pylint: disable=W0201

    def post(self, sandbox_id):
        """ the real handler for remote function execution """
        execution_service = ServerExecutionServiceSingleton(self._config)
        file_name = self.get_body_argument("file_name", default=None, strip=False)
        func_name = self.get_body_argument("func_name", default=None, strip=False)
        print('from client:', file_name, func_name)
        input_data = pickle.loads(base64.standard_b64decode(\
                self.get_body_argument("input_data", default="", strip=False)))
        output_data = execution_service.execute_code(sandbox_id, file_name, func_name, input_data)
        if not output_data is None:
            self.write(base64.standard_b64encode(pickle.dumps(output_data)))

    get = post
