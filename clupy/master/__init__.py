"""master module entry point functions"""
from __future__ import print_function
import logging
import signal
import tornado.ioloop
import tornado.web
from tornado.ioloop import PeriodicCallback
from .registration import RegistrationHandler, UnegistrationHandler
from .registration import InfoHandler, AllocServerResourcesHandler
from .registration import RetainServerResourcesHandler, ServerRegistrationServiceSingleton

class Health(tornado.web.RequestHandler):
    """master server health checking"""
    def get(self):
        """check the server health"""
        self.write("iamok")

def on_shutdown():
    """ called when user pressed ctrl + C """
    logger = logging.getLogger('master')
    logger.info("master server is shutting down")
    tornado.ioloop.IOLoop.current().stop()

def run_server(args):
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
        (r"/unregister/(.*)", UnegistrationHandler, dict(config=master_config)),
        (r"/info", InfoHandler, dict(config=master_config)),
        (r"/alloc/(.*)/(.*)", AllocServerResourcesHandler, dict(config=master_config)),
        (r"/retain/(.*)/(.*)", RetainServerResourcesHandler, dict(config=master_config)),
    ])
    application.listen(master_config.port) # pylint: disable=E1101
    logger.info('Starting master at port %d', master_config.port) # pylint: disable=E1101

    service = ServerRegistrationServiceSingleton(master_config)

    maintenance = PeriodicCallback(lambda: service.maintain_servers(), \
                    master_config.maintenance_period * 1000) # pylint: disable=E1101
    maintenance.start()

    signal.signal(signal.SIGINT, \
        lambda sig, frame: tornado.ioloop.IOLoop.current().add_callback_from_signal(on_shutdown))
    tornado.ioloop.IOLoop.current().start()
    maintenance.stop()
