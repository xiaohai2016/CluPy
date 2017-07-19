"""server node module entry point"""
from __future__ import print_function
import logging
import tornado.ioloop
import tornado.web

class Mainhandler(tornado.web.RequestHandler):
    """placeholder hadler for now"""
    def get(self):
        """placeholder routine for now"""
        self.write("Hello! This is a server node!")

def run_server(port):
    """start the server node"""
    # Enforce the existence of the clupy.server.yaml
    from ..utils.config import ServerConfigure
    config_file = 'clupy.server.yaml'
    if not ServerConfigure.exists(config_file):
        print("Error: {} file is not found".format(config_file))
        return
    server_config = ServerConfigure(config_file)

    format_string = '%(asctime)-15s, %(message)s'
    logging.basicConfig(format=format_string, level=logging.INFO)
    logger = logging.getLogger('master')

    application = tornado.web.Application([
        (r"/", Mainhandler)
    ])
    application.listen(server_config.port)
    logger.info('Starting master at port {}'.format(server_config.port))
    tornado.ioloop.IOLoop.current().start()
