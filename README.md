# CluPy
[CluPy](https://github.com/xiaohai2016/CluPy) is a simple library and framework for running Machine Learning algorithms in Python clusters. Unlike other cluster technologies, [CluPy](https://github.com/xiaohai2016/CluPy) requires minimum amount of efforts from data scientists, i.e. a simple wrapping of a function call is sufficient to automatically trigger large scale parallel executions. It also supports a number of other important features for data scientists such as simple service deployments and efficient resource sharing and flow coordination among modules.

# Major Features

## Simple Parallel Execution

Suppose you have a computation-intensive routine `expensive_computation(args)` that you would like to execute on multiple machines in parallel. With [CluPy](https://github.com/xiaohai2016/CluPy), you simply need the following line of code to invoke the computation 100 times over 50 computers.

```python
results = [clupy.parallel(expensive_computation, server_count=50)(args) for _ in range(100)]
```

## Simple Service Deployment

Suppose you successfully developed a model that does face recognition, and you'd like to deploy it to be used by the general public. You simply need to define a service file with the following contents:

```python
import clupy

clupy.service(
    packages=[list_of_dependent_packages],
    entry_points=[list_of_module_dot_function_name],
    port=8080
    )
```

and submit to a [CluPy](https://github.com/xiaohai2016/CluPy) cluster by a command:
```sh
python -m clupy --publish your_service.py --master-url your-cluster-url
```

The rest, e.g. input/output parameter marshaling, endpoint publishing, package installation, status monitoring, metrics collection etc. are all automatically handled by the framework.

## Efficient Data Sharing

For each [CluPy](https://github.com/xiaohai2016/CluPy) cluster, with simple configuration changes in the cluster, data scientists can gain access to a [Redis](https://redis.io/) based file store. One can import or export CSV, Parquet files from and into it with ease(just like regular files). Since [Redis](https://redis.io/) is memory based, the data sharing among modules are efficient.

The framework intelligently takes care of cleaning up of stale/unused data to ensure the healthy of the [Redis](https://redis.io/) cluster.

## Reliable Flow Coordinate & Synchronization

This is achieved by relying and exposing capabilities from well tested [Zookeeper](https://zookeeper.apache.org/) clusters.

## Highly Parallel Depp Learning Libraries and TensorFlow Integration

Being planned.

# Getting Started

1. To install CluPy, run:
```sh
python -m pip install clupy
```

2. To start a cluster master node, run:
```sh
# the local clupy.master.yaml file is read if it exists
python -m clupy --master
```

3. To start one or more server nodes, run:
```sh
# the master host's default value is localhost
# the master host's default port is 7878
# The local clupy.server.yaml file is loaded if it exists
python -m clupy --serve --master-url clupy://master_server_address:7878
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
  clupy.wait_all(results, time_out=10)
  for res in results:
    if res.completed:
        if not res.value is None:
            print("results: ", res.value)
        elif not res.failure is None:
            print("failure: ", res.failure)
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
* [Tornado](http://www.tornadoweb.org/en/stable/) - a Python web framework and asynchronous networking library

# Authors
* [Xiaohai Zhang](https://xiaohaionline.com)

# Links
* [ParallelProcessing](https://wiki.python.org/moin/ParallelProcessing) - a Python WIKI page regarding parallel processing in Python
* [Tornado](http://www.tornadoweb.org/en/stable/) - a Python web framework and asynchronous networking library

