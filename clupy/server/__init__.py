"""server node module entry point"""
from __future__ import print_function
import logging
import signal
import tornado.ioloop
import tornado.web
from .registration import ServerNodeRegistrationSingleton

class Health(tornado.web.RequestHandler):
    """master server health"""
    def get(self):
        """check health of the server"""
        self.write("iamok")

def on_shutdown(register_service):
    """ called when user pressed ctrl + C """
    logger = logging.getLogger('server')
    logger.info("server node is shutting down")
    register_service.stop_registration()
    tornado.ioloop.IOLoop.current().stop()

def run_server(args):
    """start the server node"""
    # Enforce the existence of the clupy.server.yaml
    from ..utils.config import ServerConfigure
    config_file = 'clupy.server.yaml'
    if not ServerConfigure.exists(config_file):
        print("Error: {} file is not found".format(config_file))
        return
    server_config = ServerConfigure(config_file)
    if args.master_url:
        server_config.config['master_url'] = args.master_url

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

    register_service = ServerNodeRegistrationSingleton(server_config)
    register_service.start_registration()

    signal.signal(signal.SIGINT, \
        lambda sig, frame: tornado.ioloop.IOLoop.current().add_callback_from_signal(\
            on_shutdown, register_service))
    tornado.ioloop.IOLoop.current().start()

