#!/usr/bin/python
#
# inithost.py
# Copyright (C) 2010 NC State University
# Written by Jack Neely <jjneely@ncsu.edu>
#
# SDG
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import optparse
import logging
import getpass
import sys
import os

from constants import *

import xmlrpc
import clientconf
import client

logger = None

uuid = client.getUUID()

def main():
    global logger

    usage = """Realm Linux Management Init Host Tool
Licensed under the GNU General Public License.
ncsurename [-C configfile] -s <secret> -f <FQDN>"""
    parser = optparse.OptionParser(usage)
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="RLMTools Configuration file")
    parser.add_option('-s', '--secret', action='store',
                      default=None,
                      dest='secret',
                      help='RLMTools Secret')
    parser.add_option('-f', '--fqdn', action='store',
                      default=None,
                      dest='fqdn',
                      help='FQDN of Host to Init')

    (options, args) = parser.parse_args()

    URL = clientconf.initConfig(options.configfile)
    logger = logging.getLogger("rlmclient")
    server = xmlrpc.setupServer(URL)

    if options.fqdn is None or options.secret is None:
        parser.print_help()
        sys.exit(1)

    # Get dept into from RLMTools
    err, sid = xmlrpc.doRPC(server.initHost, options.secret, options.fqdn)
    print sid
    sys.exit(err)


if __name__ == "__main__":
    main()

