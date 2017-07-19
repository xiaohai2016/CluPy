"""master module entry point functions"""
from __future__ import print_function
import logging
import tornado.ioloop
import tornado.web

class Mainhandler(tornado.web.RequestHandler):
    """placeholder handler for now"""
    def get(self):
        """placeholder routine for now"""
        self.write("Hello! This is master!")

def run_server(port):
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
        (r"/", Mainhandler)
    ])
    application.listen(master_config.port)
    logger.info('Starting master at port {}'.format(master_config.port))
    tornado.ioloop.IOLoop.current().start()
