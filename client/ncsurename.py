#!/usr/bin/python
#
# RealmLinux Manager -- Rename a Realm Linux client
# Copyright (C) 2009 NC State University
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
import socket
import sys
import os

from constants import *

import xmlrpc
import clientconf
import client

logger = None

key = client.getLocalKey()
uuid = client.getUUID()
sig = key.signString(uuid)

def ask_ok(prompt, retries=3, complaint='Yes or no, please!'):
    while True:
        ok = raw_input(prompt)
        ok = ok.lower()
        if ok in ('y', 'ye', 'yes'):
            return True
        if ok in ('n', 'no', 'nop', 'nope'):
            return False
        retries = retries - 1
        if retries < 0:
            raise IOError('PEBCAK Error')
        print complaint

def alterHosts(newHost):
    fd = open('/etc/hosts')
    lines = fd.readlines()
    fd.close()
    fd = open('/etc/hosts', 'w')

    for line in lines:
        if line.find(newHost[0]) > -1:
            continue
        if line.find(newHost[1]) > -1:
            continue
        fd.write(line)

    fd.close()

def alterSysconfig(newHost):
    fd = open('/etc/sysconfig/network')
    lines = fd.readlines()
    fd.close()
    fd = open('/etc/sysconfig/network', 'w')

    for line in lines:
        if line.find('HOSTNAME=') > -1:
            fd.write('HOSTNAME=%s\n' % newHost[1])
        else:
            fd.write(line)

    fd.close()

def alterMind(newHost):
    os.system("/bin/hostname %s" % newHost[1])

def main():
    global logger
    usage = """Realm Linux Management rename client tool.  
Licensed under the GNU General Public License.
ncsurename [-C configfile]"""
    parser = optparse.OptionParser(usage)
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")

    (options, args) = parser.parse_args()

    URL = clientconf.initConfig(options.configfile)
    logger = logging.getLogger("rlmclient")
    server = xmlrpc.setupServer(URL)

    if os.getuid() != 0:
        print "You are not root.  Insert error message here."
        sys.exit(1)

    logger.info("Invoked ncsurename.py with config from %s" % \
                str(options.configfile))

    newHost = xmlrpc.doRPC(server.getAddress)
    if newHost[0] == newHost[1]:
        print "ERROR: This machine's IP (%s) does not resolve." % newHost[0]
        sys.exit(1)

    print "This machine is %s with IP address %s" % (newHost[1], newHost[0])
    print "Type 'yes' to alter this machine's little mind to this hostname."
    print "Type 'no' to abort."
    print
    if not ask_ok("Alter this machine's little mind?"):
        print "User abort."
        sys.exit(0)

    logger.info("Renaming host to %s" % newHost[1])
    print "Altering /etc/hosts..."
    alterHosts(newHost)
    print "Altering /etc/sysconfig/network..."
    alterSysconfig(newHost)
    print "Altering current hostname..."
    alterMind(newHost)

    print "Altering RLMTools (Liquid Dragon) database..."
    xmlrpc.doRPC(server.resetHostname, uuid, sig)
    print "Updating RLMTools stored RHN ID for this client..."
    xmlrpc.doRPC(server.updateRHNSystemID, uuid, sig, client.getRHNSystemID())

if __name__ == "__main__":
    main()

