""" The client side remote execution engine """
from __future__ import print_function
import inspect
import logging
import pickle
import socket
import os
import threading
import queue
from tornado.httpclient import HTTPClient, HTTPError
from tornado.ioloop import IOLoop
from tornado import gen

def func_wrapper(service_object, func, func_key):
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
            return service_object.func_wrapped(packed, func, func_key)
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
                self._service = service_object
                self._logger = logging.getLogger("worker")

            @gen.coroutine
            def execute_single_call(self, call_context, server_entry):
                """ execute one function call against one given server,
                    use tornado coroutine to simplify the asynchronous
                    programming logic
                """
                pass

            def do_work(self):
                """ the place that real work is done
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
                self._logger.info("do_work entered")

            def run(self):
                self._logger.info("the remote execution worker thread started")
                self._service.queue_lock.acquire()
                while not self._service.exiting:
                    if not self._service.condition.wait(1.0):
                        self._logger.info("wait timeout")
                        continue
                    if self._service.exiting:
                        self._logger.info("awaken, exiting")
                    self._logger.info("awaken, got job to do")
                    self.do_work()
                self._service.queue_lock.release()
                self._logger.info("the remote execution worker thread is exiting")

        def __init__(self):
            self._server_lists = {}
            self._logger = logging.getLogger('client')
            self._exiting = False
            self._queue_lock = threading.Lock()
            self._condition = threading.Condition(self._queue_lock)
            self._thread = RemoteExecutionServiceSingleton.\
                            RemoteExecutionService.RemoteExecutionWorker(self)
            self._thread.start()

        def stop_work(self):
            """ stop the worker thread """
            if self._thread:
                self._exiting = True
                self._queue_lock.acquire()
                self._condition.notify_all()
                self._queue_lock.release()
                self._thread.join()
                self._thread = None
                self._condition = None
                self._queue_lock = None

        @property
        def exiting(self):
            """ return if exiting property """
            return self._exiting

        @property
        def queue_lock(self):
            """ return the queue lock object property """
            return self._queue_lock

        @property
        def condition(self):
            """ return the condition object """
            return self._condition

        def func_wrapped(self, packed, func, func_key):
            """ the wrapped function of the passed-in func to capture parameters """
            context = self._server_lists[func_key]
            file_name = inspect.getfile(func)
            # 1. now we are ready to create a single invocation context
            invocation_context = OneExecutionRequestContext(context, func_key, file_name, func.__name__, packed)
            # 2. Stick the invocation context into a rquest queue, notify the worker thread
            self._queue_lock.acquire()
            self._condition.notify()
            self._queue_lock.release()
            # 3. Wrap the invocation context into a Future object to return
            return RemoteExecutionFuture(invocation_context)

        def execute(self, func, server_count):
            """ remotely execute the function with a specified maximum number of server involved
                Workflow:
            # In caller's thread context:
            # 1. From the master node, get a set of servers to perform the calculation
            # 2. For each method (that is to be remotely invoked), create a RemoteFunctionContext
            # 3. Return a wrapped function object, when called, package all the
            #    parameters into a dictionary
            # 4. Pack the parameter dictionary along with other information into a
            #    OneExecutionRequestContext
            # 5. With the execution context, notify the worker thread to carry out remote invocation
            # 5. From the execution context, return the Future object to the caller, so that callers
            #    can check states or wait for completion
            # Worker's thread context - main routine:
            # 1. Based on the request queue, check if a server is available
            # 2. Ask the remote server to create a sandbox,gets back a sandbox id
            # 3. Potentially upload source codes into the newly created sandbox
            # 4. Ask the server to execute the given function with the given data
            # 5. Retain servers from the master node if it is time
            # Worker's thread context - invocation callback:
            # 1. Potentially ship over all the log information and stack backtraces
            # 2. Mark the corresponding Future object as succeeded/failed/completed
            # 3. Mark the server object as "free"
            # 4. Notify the caller's thread context if waiting
            # 5. retain the server list from the master node if it is time
            # Server's execution context
            # 1. Unpack the input data
            # 2. Invoke the function
            # 3. Pack the return data
            # 4. Send the response
            # 5. Clean sandbox data and ship over logs
            # 6. Close down
            """

            func_key = inspect.getfile(func) + ":" + func.__name__
            if not func_key in self._server_lists.keys() \
                    or len(self._server_lists[func_key].server_list) == 0: #pylint: disable=C1801
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
                        context = RemoteFunctionContext()
                        context.server_list = pickle.loads(response.body)
                        self._server_lists[func_key] = context
                        self._logger.info("master returned server list: %s", \
                                            str(context.server_list))
                except HTTPError as err:
                    self._logger.error("request servers from master got HTTP error: %s", str(err))
                except ConnectionRefusedError as conn_err: # pylint: disable=E0602
                    self._logger.error("Connection error: %s", str(conn_err))
                http_client.close()
            # raise HTTPError in case we still do not have the server list
            if not func_key in self._server_lists.keys():
                raise HTTPError("could not get server list from the master at {}".\
                        format(RemoteExecutionServiceSingleton.master_url))

            # now return a function to capture the input parameters, passing along the context
            return func_wrapper(self, func, func_key)

class RemoteFunctionContext(object):
    """ context information for a function that is to be remotedly invoked """

    def __init__(self):
        self.server_list = []

class OneExecutionRequestContext(object):
    """ context information for a single remote execution request """

    def __init__(self, remote_function_context, func_key, source_file, func_name, input_data):
        self.remote_function_context = remote_function_context
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
        pass

    def succeed(self, suceed_callback):
        """ setting the suceed_callback function """
        self._suceed_callback = suceed_callback

    def fail(self, fail_callback):
        """ setting the fail_callback function """
        self._fail_clallback = fail_callback

    def complete(self, succeed_callback, fail_callback):
        """ setting the completion callback functions """
        self._suceed_callback = succeed_callback
        self._fail_clallback = fail_callback