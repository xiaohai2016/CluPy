""" The client side remote execution engine """
from __future__ import print_function
import inspect
import logging
import pickle
import socket
import os
import threading
from datetime import datetime
import queue
from tornado.httpclient import HTTPClient, HTTPError
from tornado.ioloop import IOLoop
from tornado import gen

def func_wrapper(service_object, func, server_count):
    """ the function for wrapping func """
    argspec = inspect.getargspec(func)

    class MyWrapper(object):
        """ the wrapped function object """
        def __call__(self, *args, **kwargs):
            packed = {}
            index = 0
            if argspec.args:
                for arg in argspec.args:
                    packed[arg] = args[index]
                    index = index + 1
            if argspec.varargs:
                for arg in argspec.varargs:
                    packed[arg] = args[index]
                    index = index + 1
            if argspec.keywords:
                for arg in argspec.keywords:
                    packed[arg] = argspec.defaults[index] if args[index] is None else args[index]
                    index = index + 1
            return service_object.func_wrapped(packed, func, server_count)
    return MyWrapper()

class RemoteExecutionServiceSingleton(object):
    """ make RemoteExecutionService a singleton object """

    instance = None
    master_url = None
    client_id = None

    def __new__(cls):
        """ service instance creation """
        if not RemoteExecutionServiceSingleton.instance:
            RemoteExecutionServiceSingleton.instance = \
                RemoteExecutionServiceSingleton.RemoteExecutionService()
            RemoteExecutionServiceSingleton.client_id = socket.gethostname() \
                    + ":" + str(os.getpid())
        return RemoteExecutionServiceSingleton.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, val):
        return setattr(self.instance, name, val)

    class RemoteExecutionService(object):
        """ the entry point service for remote execution """

        class RemoteExecutionWorker(threading.Thread):
            """ the worker thread for RemoteExecutionService """
            def __init__(self, service_object):
                threading.Thread.__init__(self)
                self._function_list = {}
                self._logger = logging.getLogger("worker")

            def remote_execution_request(self, func, packed, future_obj, server_count):
                """ the callback function added when there is a remote excution request
                    1. For the remtely executed function, synchronously rquest the list of
                       servers from the master node (if has not). Each server's information
                       is kept in a RemoteServerInfo structure. The list of the servers is
                       saved in the RemoteFunctionContext structure.
                    2. Pack the request information into a OneExecutionRequestContext structure,
                       and save it as a queue element inside the RemoteFunctionContext structure
                    3. Carryout execution if opptunities exist
                    4. Maintain server status: refresh server list if active, deregister if inactive
                """
                self._logger.info("remote execution request received by the worker")

                file_name = inspect.getfile(func)
                func_key = file_name + ":" + func.__name__
                if not func_key in self._function_list.keys() \
                        or len(self._function_list[func_key].server_list) == 0: #pylint: disable=C1801
                    # need to request for a list of servers to remotely execute this function
                    master_url = RemoteExecutionServiceSingleton.master_url.replace(\
                        "clupy://", "http://")
                    master_url = master_url.rstrip('/')
                    master_url = master_url + "/alloc/" + RemoteExecutionServiceSingleton.client_id \
                        + "/" + str(server_count)
                    http_client = HTTPClient()
                    try:
                        response = http_client.fetch(master_url)
                        if response.error:
                            self._logger.error("request servers from master got error: %s", \
                                                str(response.error))
                        else:
                            function_context = RemoteFunctionContext()
                            server_list = pickle.loads(response.body)
                            function_context.server_list = []
                            for server in server_list:
                                function_context.server_list.append(RemoteServerInfo(server))
                            self._function_list[func_key] = function_context
                            self._logger.info("master returned server list: %s", \
                                                str(server_list))
                    except HTTPError as err:
                        self._logger.error("request servers from master got HTTP error: %s", str(err))
                    except ConnectionRefusedError as conn_err: # pylint: disable=E0602
                        self._logger.error("Connection error: %s", str(conn_err))
                    http_client.close()

                # raise HTTPError in case we still do not have the server list
                if not func_key in self._function_list.keys():
                    raise HTTPError("could not get server list from the master at {}".\
                            format(RemoteExecutionServiceSingleton.master_url))
                function_context = self._function_list[func_key]

                # 1. now we are ready to create a single invocation context
                invocation_context = OneExecutionRequestContext(future_obj, func_key, file_name, func.__name__, packed)
                # 2. Stick the invocation context into a rquest queue
                if function_context.task_queue is None:
                    function_context.task_queue = queue.Queue()
                function_context.task_queue.put(invocation_context)

                self.carry_out_executions()

                self.maintain_server_states()

            def stop_worker_request(self):
                """ called from the main thread to stop the worker"""
                IOLoop.current().stop()

            @gen.coroutine
            def execute_single_call(self, call_context, server_entry):
                """ execute one function call against one given server,
                    use tornado coroutine to simplify the asynchronous
                    programming logic
                """
                self._logger.info("execute single call invoked")
                return

            def complete_single_execution(self, result, excep, call_context, server_entry):  # pylint: disable=W0613
                """ mark the completion of a single execution"""
                self._logger.info("completing a single execution: %s", call_context.func_key)
                call_context.future_object.value = result if not result is None else excep
                call_context.future_object.do_complete_callback(result, excep)
                server_entry.one_execution_context = None
                self.carry_out_executions()
                self.maintain_server_states()

            def carry_out_executions(self):
                """ Check to carry out any permissible remote executions
                    # break out in the middle any time if the system is exiting
                    # 1. Check if we have a server resource that is available for execution
                    #    Check if we have a task waiting in the queue
                    #    Loop until one of the above is False
                    #    1.1. Issue the execution of one async task against one serve,
                    #         record the future object
                    # 2. Mark all completed future objects for completion (one execuition is done)
                    # 3. For remote function contexts that are 30 seconds or more idel, release them
                    # 4. For remote function contexts that are expiring, and were active in the
                    #    past 30 seconds, renew the lease
                """
                for _, func_context in self._function_list.items():
                    if not func_context.task_queue.empty():
                        available_server = None
                        for server in func_context.server_list:
                            if server.one_execution_context is None:
                                available_server = server
                                break
                        if available_server:
                            # Got a free server along as a request
                            available_server.one_execution_context = func_context.task_queue.get()
                            call_future = self.execute_single_call(\
                                    available_server.one_execution_context, available_server)
                            available_server.last_activity_time = datetime.now()
                            IOLoop.current().add_future(call_future, lambda fut, av=\
                                available_server: self.complete_single_execution(\
                                    fut.result(), None, av.one_execution_context, av))

            def maintain_server_states(self):
                """ renew server lease for active servers, release idel servers """
                pass

            def run(self):
                self._logger.info("the remote execution worker thread started")
                IOLoop.current().start()
                self._logger.info("the remote execution worker thread is exiting")

        def __init__(self):
            self._logger = logging.getLogger('client')
            self._thread = RemoteExecutionServiceSingleton.\
                            RemoteExecutionService.RemoteExecutionWorker(self)
            self._thread.start()

        def stop_work(self):
            """ stop the worker thread """
            if self._thread:
                IOLoop.current().add_callback(
                    RemoteExecutionServiceSingleton.RemoteExecutionService.\
                                RemoteExecutionWorker.stop_worker_request,
                    self._thread
                )
                self._thread.join()
                self._thread = None

        def func_wrapped(self, packed, func, server_count):
            """ the wrapped function of the passed-in func to capture parameters """

            my_future = RemoteExecutionFuture(None)
            IOLoop.current().add_callback(\
                    RemoteExecutionServiceSingleton.RemoteExecutionService.\
                            RemoteExecutionWorker.remote_execution_request,
                    self._thread, func, packed, my_future, server_count)
            return my_future

        def execute(self, func, server_count):
            """ remotely execute the function with a specified maximum number of server involved
                return a function to capture the input parameters, passing along the context
            """
            return func_wrapper(self, func, server_count)

class RemoteServerInfo(object):
    """ the server information structure represented a remote server
        containing server URL as well as an outstanding RemoteExecutionFuture object
        if any
    """

    def __init__(self, url):
        self.server_url = url
        self.one_execution_context = None
        self.last_activity_time = datetime.now()

class RemoteFunctionContext(object):
    """ context information for a function that is to be remotedly invoked """

    def __init__(self):
        self.server_list = []
        self.task_queue = None

class OneExecutionRequestContext(object):
    """ context information for a single remote execution request """

    def __init__(self, future_object, func_key, source_file, func_name, input_data):
        self.future_object = future_object
        self.func_key = func_key
        self.source_file = source_file
        self.func_name = func_name
        self.input_data = input_data

class RemoteExecutionFuture(object):
    """ the Future object for a single remote invocation """

    def __init__(self, one_execution_request_context):
        self._execution_context = one_execution_request_context
        self.successful = False
        self.completed = False
        self.value = None
        self.failure = None
        self._suceed_callback = None
        self._fail_clallback = None

    def wait(self, time_out=10):
        """ wait for the completion of the execution """
        import time
        wait_time = 0.0
        while not self.completed and (time_out == 0 or wait_time < float(time_out)):
            time.sleep(0.1)
            if time_out > 0:
                wait_time = wait_time + 0.1

    def succeed(self, suceed_callback):
        """ setting the suceed_callback function """
        self._suceed_callback = suceed_callback
        return self

    def fail(self, fail_callback):
        """ setting the fail_callback function """
        self._fail_clallback = fail_callback
        return self

    def complete(self, succeed_callback, fail_callback):
        """ setting the completion callback functions """
        self._suceed_callback = succeed_callback
        self._fail_clallback = fail_callback
        return self

    def do_complete_callback(self, result, excep):
        """ notify client about async results """
        self.completed = True
        if result:
            self.successful = True
            if self._suceed_callback:
                self._suceed_callback(result)
        if excep:
            self.successful = False
            if self._fail_clallback:
                self._fail_clallback(excep)