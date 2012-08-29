#!/usr/bin/python

import sys
import optparse
import logging
import logging.handlers

from rlmtools import rlattributes
from rlmtools import apiServer
from rlmtools import configDragon
from rlmtools.constants import defaultConfFiles

def getDept(uuid):
    RLA = rlattributes.RLAttributes()
    api = apiServer.APIServer(2, "hostname", uuid)
    host_id = api.getUuidID(uuid)
    if host_id is None:
        # Unregistered host
        return None

    dept = api.getDeptName(api.getHostDept(host_id))
    return dept

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
            default=defaultConfFiles,
            dest="configfile",
            help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases of RLMTools
    configDragon.initConfig(options.configfile)
    log = logging.getLogger("xmlrpc.enc")

    argc = len(args)

    if argc < 1:
        log.error("getdept.py called without UUID as first argument")
        sys.exit(1)

    uuid = args[0]
    dept = getDept(uuid)
    if dept is None:
        sys.exit(1)
    else:
        sys.stdout.write(dept)


if __name__ == "__main__":
    main()

