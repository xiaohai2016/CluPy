""" clupy server node registration handling """
from __future__ import print_function
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse # pylint: disable=E0611, E0401
import pickle
import pprint
import tornado.web

class ServerRegistrationInfo(object):
    """ registration information struct """
    def __init__(self):
        """ initialize the empty object """
        now = datetime.now()
        self.registration_time = now # first registration time
        self.updating_time = now # last information update time from the server
        self.reservation_time = None # first reservation time by a client
        self.last_reservation_time = None # first reservation time by a client
        self.client_id = None # id of the client that is owning the server

class ServerRegistrationServiceSingleton(object):
    """ the singleton server registration service class """

    instance = None

    def __new__(cls, config):
        """ service instance creation """
        if not ServerRegistrationServiceSingleton.instance:
            ServerRegistrationServiceSingleton.instance = \
                ServerRegistrationServiceSingleton.ServerRegistrationService(config)
        return ServerRegistrationServiceSingleton.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, val):
        return setattr(self.instance, name, val)

    class ServerRegistrationService(object):
        """ the real server registration service class """
        def __init__(self, config):
            """ pass in and save the server configuration object """
            self._config = config
            self._registrations = {}
            self._logger = logging.getLogger('master')

        def register_server(self, server_url):
            """ server node registration/update """
            self._logger.info("to register: %s", server_url)
            self._registrations[server_url] = ServerRegistrationInfo()

        def maintain_servers(self):
            """ server registration maintenance method
            to be invoked on a periodical basis """
            now = datetime.now()
            delta = timedelta(seconds=self._config.registration_ttl)
            expiration = now - delta
            for k, val in self._registrations.items():
                if val.update_time < expiration:
                    logging.info("removing server %s from registration, last update %s", \
                        k, str(val.updating_time))
                    del self._registrations[k]

        def allocate_server_resources(self, client_id, request_server_count):
            """ server computing resource allocation requests,
            for now, we only pass the server count, in the future,
            we will need to support a lot more information """

            now = datetime.now()
            delta = timedelta(seconds=self._config.reservation_ttl)
            expiration = now - delta
            return_server_list = []
            if request_server_count == 0:
                request_server_count = self._config.default_server_request_count
            if request_server_count > len(self._registrations):
                self._logger.error("requested server count %d exceeds total registration %d", \
                    request_server_count, len(self._registrations))
                return -1, ''
            for k, val in self._registrations.items():
                if val.client_id is None or val.last_reservation_time < expiration:
                    return_server_list.append(k)
                    if len(return_server_list) >= request_server_count:
                        break
            if len(return_server_list) < request_server_count:
                self._logger.info("only have %d free servers, requesting %d, trying to add busy servers", \
                                    len(return_server_list), request_server_count)
                for k, val in self._registrations.items():
                    if k not in return_server_list:
                        return_server_list.append(k)
                    if len(return_server_list) >= request_server_count:
                        break
            for server in return_server_list:
                srv_obj = self._registrations[server]
                srv_obj.reservation_time = now
                srv_obj.last_reservation_time = now
                srv_obj.client_id = client_id
            self._logger.info("returned server list: %s", pprint.pformat(return_server_list))
            return 0, return_server_list

        def retain_server_resources(self, client_id, server_list, to_free=False):
            """ retain onwership of a set of servers """

            now = datetime.now()
            for server in server_list:
                if server in self._registrations.keys():
                    srv_obj = self._registrations[server]
                    if to_free:
                        self._logger.info("client %s is releasing the server: %s", client_id, server)
                        srv_obj.client_id = None
                    else:
                        self._logger.info("client %s retained service of the server: %s", client_id, server)
                        srv_obj.last_reservation_time = now

        def query_master_info(self):
            """ return the server usage information """
            self._logger.info("-----master server info start------")
            for k, val in self._registrations.items():
                self._logger.info("%s: reg - %s, upd - %s, lrsv - %s, cid - %s", k, \
                    str(val.registration_time), str(val.updating_time), \
                    str(val.last_reservation_time), str(val.client_id))
            self._logger.info("-----master server info end------")
            return self._registrations

class MasterHandler(tornado.web.RequestHandler):
    """ the master server handler base class """

    def initialize(self, config=None):
        """ handler initialization, called for each request """
        self._service = ServerRegistrationServiceSingleton(config) # pylint: disable=W0201
        self._logger = logging.getLogger('master') # pylint: disable=W0201

class RegistrationHandler(MasterHandler):
    """ the registration handler for /register """
    def get(self, server_url):
        """ the get request handler """
        server_url = urlparse(server_url).geturl()
        self._logger.info("handling registration request for %s", server_url)

        self._service.register_server(server_url)
        response = "{} successfully registered".format(server_url)
        self._logger.info(response)
        self.write(response)

class InfoHandler(MasterHandler):
    """ returns information from the registration server """
    def get(self):
        """ the get request handler """
        reg = self._service.query_master_info()
        self.write(pickle.dumps(reg))
        self.finish()

class AllocServerResourcesHandler(MasterHandler):
    """ handler for server resources allocation request """
    def get(self, client_id, server_count):
        """ the get request handler """
        try:
            server_count = int(server_count)
        except ValueError:
            server_count = 0
        self._logger.info("handling server resources allocation request from - %s, count - %d", \
            client_id, server_count)

        code, server_list = self._service.allocate_server_resources(client_id, server_count)
        if code == 0:
            self.write(pickle.dumps(server_list))
        else:
            self.set_status(406)
            self.write("resource request can not be satisfied")
        self.finish()

class RetainServerResourcesHandler(MasterHandler):
    """ handler for retaining server resources requested earlier """
    def get(self, client_id, to_free):
        """ the get request handler """
        #server_list = self.get_body_argument("data", default=None, strip=False)
        #server_list = pickle.loads(server_list)
        server_list = ['server1']
        self._logger.info("handling resource retaining request for %s, to_free: %s, servers: %s", \
            client_id, str(to_free), pprint.pformat(server_list))
        to_free = True if int(to_free) != 0 else False
        self._service.retain_server_resources(client_id, server_list, to_free)
        self.write("server resources retained")