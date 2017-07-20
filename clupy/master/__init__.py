"""master module entry point functions"""
from __future__ import print_function
import logging
import tornado.ioloop
import tornado.web
from .registration import RegistrationHandler, InfoHandler, AllocServerResourcesHandler, RetainServerResourcesHandler

class Health(tornado.web.RequestHandler):
    """master server health checking"""
    def get(self):
        """check the server health"""
        self.write("iamok")

def run_server():
    """starting the master server"""
    # Enforce the existence of the clupy.master.yaml
    from ..utils.config import MasterConfigure
    config_file = 'clupy.master.yaml'
    if not MasterConfigure.exists(config_file):
        print("Error: {} file is not found".format(config_file))
        return
    master_config = MasterConfigure(config_file)

    format_string = '%(asctime)-15s, %(message)s'
    logging.basicConfig(format=format_string, level=logging.INFO)
    logger = logging.getLogger('master')

    application = tornado.web.Application([
        (r"/health", Health),
        (r"/register/(.*)", RegistrationHandler, dict(config=master_config)),
        (r"/info", InfoHandler, dict(config=master_config)),
        (r"/alloc/(.*)/(.*)", AllocServerResourcesHandler, dict(config=master_config)),
        (r"/retain/(.*)/(.*)", RetainServerResourcesHandler, dict(config=master_config)),
    ])
    application.listen(master_config.port) # pylint: disable=E1101
    logger.info('Starting master at port %d', master_config.port) # pylint: disable=E1101
    tornado.ioloop.IOLoop.current().start()
