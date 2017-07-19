"""execution codes for the clupy package/module"""
import argparse

MAIN_PARSER = argparse.ArgumentParser(description='Simple Clusters for Python')
MAIN_PARSER.add_argument('-m', '--master', action='store_true', help='to start a master node')
MAIN_PARSER.add_argument('-s', '--server', action='store_true', help='to start a server node')
MAIN_PARSER.add_argument('--master-url', help='to specify master server url')
MAIN_PARSER.add_argument('-c', '--client', action='store_true', help="to run in client mode")

MAIN_ARGS = MAIN_PARSER.parse_args()

if MAIN_ARGS.client:
    MAIN_ARGS.server = False
    MAIN_ARGS.master = False
if MAIN_ARGS.server:
    MAIN_ARGS.master = False

if MAIN_ARGS.master:
    from .master import run_server
    run_server(7878)

if MAIN_ARGS.server:
    from .server import run_server
    run_server(7877)