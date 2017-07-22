"""execution codes for the clupy package/module"""
from __future__ import print_function
import argparse
from .client import commands

MAIN_PARSER = argparse.ArgumentParser(description='Simple Clusters for Python')
MAIN_PARSER.add_argument('-m', '--master', action='store_true', help='to start a master node')
MAIN_PARSER.add_argument('-s', '--server', action='store_true', help='to start a server node')
MAIN_PARSER.add_argument('--master-url', help='to specify master server url')
MAIN_PARSER.add_argument('-c', '--client', help="to run in client mode")

MAIN_ARGS = MAIN_PARSER.parse_args()

if MAIN_ARGS.client:
    MAIN_ARGS.server = False
    MAIN_ARGS.master = False
if MAIN_ARGS.server:
    MAIN_ARGS.master = False

if MAIN_ARGS.master:
    from .master import run_server
    run_server(MAIN_ARGS)

if MAIN_ARGS.server:
    from .server import run_server
    run_server(MAIN_ARGS)

if MAIN_ARGS.client:
    if MAIN_ARGS.client.lower() == "info":
        if MAIN_ARGS.master_url is None:
            print("Error: must provide --master_url information")
        else:
            COMMAND_OBJ = commands.ClientCommand(MAIN_ARGS)
            COMMAND_OBJ.query_master_info()