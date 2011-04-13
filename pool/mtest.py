#!/usr/bin/python26

import time
import logging
import multiprocessing

from multiprocessing import managers

semaphore = multiprocessing.BoundedSemaphore(3)

class MathsClass(object):
    def acquire(self):
        print "Acquiring semaphore"
        semaphore.acquire()
        print "semaphore acquired"
    def release(self):
        semaphore.release()
        print "semaphore released"
    def add(self, x, y):
        return x + y
    def mul(self, x, y):
        return x * y
    def wait(self):
        time.sleep(10)

class MyManager(managers.SyncManager): pass

MyManager.register('Maths', MathsClass)

def main():
    print "Testing multiprocessing"
    logger = multiprocessing.log_to_stderr()
    logger.setLevel(logging.DEBUG)

    sm = MyManager("/tmp/python-socket", "key")
    sm.get_server().serve_forever()


if __name__ == "__main__":
    main()

