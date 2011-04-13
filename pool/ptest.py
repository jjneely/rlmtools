#!/usr/bin/python26

import multiprocessing
import logging

from multiprocessing import managers

class MyManager(managers.SyncManager): pass

MyManager.register('Maths')

def main():
    print "Multiprocessing client test"
    logger = multiprocessing.log_to_stderr()
    logger.setLevel(logging.DEBUG)

    sm = MyManager("/tmp/python-socket", "key")
    sm.connect()

    m = sm.Maths()
    m.acquire()
    for i in range(10):
        print m.mul(i, i)
        m.wait()
    m.release()

if __name__ == "__main__":
    main()

