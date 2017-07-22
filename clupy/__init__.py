""" the entry point of the CluPy package """
from __future__ import print_function
from .client.execution import RemoteExecutionServiceSingleton

def set_master_url(master_url):
    """ set the master URL for remote methods invocation """
    RemoteExecutionServiceSingleton.master_url = master_url

def parallel(func, server_count=0):
    """ the routine to parallize the execution of func across the cluster """
    remote_execution = RemoteExecutionServiceSingleton()
    return remote_execution.execute(func, server_count)

def wait_all(futures, time_out=0):
    """ waits for the completion of a list of Future objects """
    print('wait_all called')

def stop_remote_execution():
    """ stops all remote execution related stuff """
    remote_execution = RemoteExecutionServiceSingleton()
    remote_execution.stop_work()
