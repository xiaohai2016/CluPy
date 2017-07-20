"""server node module entry point"""
from __future__ import print_function
import logging
import tornado.ioloop
import tornado.web

class Health(tornado.web.RequestHandler):
    """master server health"""
    def get(self):
        """check health of the server"""
        self.write("iamok")

def run_server():
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
        (r"/health", Health)
    ])
    sockets = tornado.netutil.bind_sockets(server_config.port) # pylint: disable=E1101
    server = tornado.httpserver.HTTPServer(application)
    server.add_sockets(sockets)
    for sock in sockets:
        server_config.config['port'] = sock.getsockname()[1]
        break
    logger.info('Starting server node at port %d', server_config.port) # pylint: disable=E1101


    tornado.ioloop.IOLoop.current().start()
