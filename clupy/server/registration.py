""" server node registration with the master node processing """
from __future__ import print_function
import logging
import urllib
from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPError
import tornado.ioloop

class ServerNodeRegistrationSingleton(object):
    """ the singleton class for server node registration with the master nodes """

    instance = None

    def __new__(cls, config):
        """ service instance creation """
        if not ServerNodeRegistrationSingleton.instance:
            ServerNodeRegistrationSingleton.instance = \
                ServerNodeRegistrationSingleton.ServerNodeRegistration(config)
        return ServerNodeRegistrationSingleton.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, val):
        return setattr(self.instance, name, val)

    class ServerNodeRegistration(object):
        """ the management class for server node registrations with the master nodes """

        def __init__(self, config):
            self._config = config
            self._logger = logging.getLogger("server")
            self._timeout_handle = None
            self._stopped = False
            self._http_request = None

        def process_registration_response(self, response):
            """ processing registration request response """
            if response.error:
                self._logger.error("registration request error: %s", response.error)
                timeout = self._config.failure_retry_interval
            else:
                self._logger.info("successful in server registration")
                timeout = self._config.registration_interval
            if self._timeout_handle is not None:
                tornado.ioloop.IOLoop.current().remove_timeout(self._timeout_handle)
                self._timeout_handle = None
            if not self._stopped:
                self._timeout_handle = tornado.ioloop.IOLoop.current().call_later(timeout, \
                    self.start_registration)

        def start_registration(self):
            """ start the registration process """
            self._logger.info("issuing registration request")
            master_url = self._config.master_url.replace("clupy://", "http://")
            master_url = master_url if master_url.endswith("/") else master_url + "/"
            server_url = urllib.parse.quote_plus(self._config.server_url) # pylint: disable=E1101
            master_url = master_url + "register/" + server_url
            if self._http_request is not None:
                self._http_request.close()
            self._http_request = AsyncHTTPClient()
            self._http_request.fetch(master_url, \
                lambda response, context=self: context.process_registration_response(response))

        def stop_registration(self):
            """ stop the server node registration, called upon exiting """
            self._logger.info("stopping server node registration")
            master_url = self._config.master_url.replace("clupy://", "http://")
            master_url = master_url if master_url.endswith("/") else master_url + "/"
            server_url = urllib.parse.quote_plus(self._config.server_url) # pylint: disable=E1101
            master_url = master_url + "unregister/" + server_url
            http_client = HTTPClient()
            try:
                http_client.fetch(master_url)
            except HTTPError as err:
                self._logger.error("stopping server node registration error: %s", str(err))
            http_client.close()
            self._stopped = True

