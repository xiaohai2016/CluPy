# CluPy
[CluPy](https://github.com/xiaohai2016/CluPy) is a simple clustering library and framework for parallel executions in Python. Unlike other prallel processing and clustering technologies, [CluPy](https://github.com/xiaohai2016/CluPy) hides all the clustering delecacies from programmers. A simple wrapping of a function call is sufficient to turn a local function call to be executed in a cluster and thus allowing parallelism among multiple invocations.

At the same time, resources registraion, management, coordination and system configurations are all designed to be simple and intuitive.

Built upon the success of [Redis](https://redis.io/) and [Zookeeper](https://zookeeper.apache.org/), [CluPy](https://github.com/xiaohai2016/CluPy) also provides simplified and yet efficient set of APIs for data sharing and multiprocess coordination/synchronization.

# Getting Started

1. To install CluPy, run:
```sh
python -m pip install clupy
```

2. To start a cluster master node, run:
```sh
# the local clupy.master.yaml file is read if it exists
python -m clupy master
```

3. To start one or more server nodes, run:
```sh
# the master host's default value is localhost
# the master host's default port is 7878
# The local clupy.server.yaml file is loaded if it exists
python -m clupy serve --master master_server_address --port 7878
```

4. From your client codes, to start parallel executions of a method, wrap around the method call with `clupy.parallel(original_method)` to make the local method execute in the cluster:
```python
import clupy

def primes(n):
    divisors = [ d for d in range(2,n//2+1) if n % d == 0 ]
    return [ d for d in divisors if \
             all( d % od != 0 for od in divisors if od != d ) ]

if __name__ == "__main__":
  # The client configure information is read off the local clupy.client.yaml file if exists
  results = [clupy.parallel(primes, max=10)(n) for n in range(100, 200)]
  clupy.wait_all(time_out=10s, results)
  for r in results:
    if r.successful:
      print(r.value)
    else:
      print(r.failure)
```

On the client side, you can also use the following calling style
```python
if __name__ == "__main__":
  results = [clupy.parallel(primes, max=10)(n) for n in range(100, 200)]
  for r in results:
    r.succeed(x: print(x)).fail(x: print(x))
  clupy.wait_all(time_out=10s, results)
```

When a function is wrapped with `clupy.parallel(original_method)`, the real return value of the wrapped function is changed into a `Future` object encapsulating the original return value and possibly some failure information (exceptions thrown). The `Future` class has the following prototype:
```python
class Future(object):
  def __init__(self):
    # a boolean indicating success or failure
    self.successful = False
    # a boolean indicating if the call has finished
    self.completed = False
  def succeed(self, lambda):
    # Upon a successful completion, executes the lambda function with the successful return values
    # and returns the same Future object
  def fail(self, lambda):
    # Upon completion and a failure, executes the lambda function with the failure information
    # and returns the same Future object
  def wait(self, timeout=10s):
    # Wait for the completion of the execution with a timeout
```

# Discussions

## Version compatibility

To avoid compatibility issues, the master nodes, server nodes and client nodes MUST all be running the same major Python versions. Otherwise, errors will be raised.

## Library dependencies

The master node, through the `clupy.master.dependency.yaml` file, defines default set of Python libraries available on all server nodes. Server nodes periodically syncs with the master node(s) to install/upgrade additional libraries if any.

Client nodes will return error or warning if libraries in its environment differ from those of the master node(s).

For any additional library dependencies, the client side is responsible for authoring a `clupy.client.dependency.yaml` file outlining all required libraries that are needed.

# Dependencies
* [Tornadio](http://www.tornadoweb.org/en/stable/) - a Python web framework and asynchronous networking library

# Authors
* [Xiaohai Zhang](https://xiaohaionline.com)

# Links
* [ParallelProcessing](https://wiki.python.org/moin/ParallelProcessing) - a Python WIKI page regarding parallel processing in Python
* [Tornadio](http://www.tornadoweb.org/en/stable/) - a Python web framework and asynchronous networking library

