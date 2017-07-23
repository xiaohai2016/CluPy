""" The testing module to verify the functionaliy of CluPy """
from __future__ import print_function
import logging
import clupy
import pickle
import base64

def primes(num):
    """ find prime factors of num """
    divisors = [d for d in range(2, num//2 + 1) if num % d == 0]
    return [d for d in divisors if \
             all(d % od != 0 for od in divisors if od != d)]

def plain_execution():
    """ simple & old fasioned serialized execution """
    results = [primes(n) for n in range(10000, 10009)]
    print('plain: ', results)

def parallel_execution():
    """ new parallel execution model """
    #logging.basicConfig(level=logging.INFO)
    clupy.set_master_url("clupy://localhost:7878")

    results = [clupy.parallel(primes, server_count=2)(n) for n in range(10000, 10009)]
    clupy.wait_all(results, time_out=10)
    for res in results:
        if res.completed:
            if not res.value is None:
                print("results: ", res.value)
            elif not res.failure is None:
                print("failure: ", res.failure)

    clupy.stop_remote_execution()

if __name__ == "__main__":
    plain_execution()
    parallel_execution()
