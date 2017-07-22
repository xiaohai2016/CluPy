""" client side commands support """
from __future__ import print_function
import logging
import pickle
from tornado.httpclient import HTTPClient, HTTPError
import tornado.ioloop

class ClientCommand(object):
    """ the class that supports issue commands on the client side """
    def __init__(self, args):
        self._master_url = args.master_url
        self._args = args
        self._logger = logging.getLogger('client')

    def query_master_info(self):
        """ to query information from master server node """
        master_url = self._master_url.replace("clupy://", "http://")
        master_url = master_url.rstrip('/')
        master_url = master_url + "/info"
        http_client = HTTPClient()
        try:
            response = http_client.fetch(master_url)
            if response.error:
                self._logger.error("Connection error: %s", str(response.error))
            else:
                registrations = pickle.loads(response.body)
                for k, val in registrations.items():
                    print("{} -> ".format(k))
                    print("      register_time: {}".format(val.registration_time))
                    print("      update_time: {}".format(val.updating_time))
                    print("      reserve_time: {}".format(val.reservation_time))
                    print("      reserve_update_time: {}".format(val.last_reservation_time))
                    print("      client_id: {}".format(val.client_id))
        except HTTPError as err:
            self._logger.error("stopping server node registration error: %s", str(err))
        except ConnectionRefusedError as conn_err: # pylint: disable=E0602
            self._logger.error("Connection error: %s", str(conn_err))
        http_client.close()
