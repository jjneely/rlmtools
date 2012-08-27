#!/usr/bin/python
#
# RealmLinux Manager -- Rename a Realm Linux client
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
import socket
import sys
import os

from types import StringType
from constants import *

import xmlrpc
import clientconf
import client

logger = None

uuid = client.getUUID()
keypair = client.getLocalKey()
sig = keypair.signString(uuid)

def dept_search_list(dept):
    # dept - Local department string
    # returns a list of departments, in order, to search for puppet repos
    if isinstance(dept, StringType):
        return dept_search_list([dept.replace("-", "_")])

    i = dept[0].split("_")
    i = "_".join(i[:-1])

    if i == '':
        return ["root"] + dept
    else:
        return dept_search_list( [i] + dept )


def parse_cmd():
    usage = """Realm Linux Management Puppet/Bcfg2 Boot Strap Tool.
This tool will setup your Configuration Management (CM) Tool.\n
Licensed under the GNU General Public License.
ncsurename [-C configfile]"""
    parser = optparse.OptionParser(usage)
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="RLMTools Configuration file")
    parser.add_option("-B", "--bcfg2", action="store_true",
                      default=False,
                      dest='bcfg2',
                      help="Use Bcfg2 as your CM System")
    parser.add_option("-P", "--puppet", action="store_true",
                      default=False,
                      dest='puppet',
                      help="Use Puppet as your CM System")
    parser.add_option('-x', '--password', action='store',
                      default=None,
                      dest='password',
                      help='Bcfg2 Repository/Communication Password')
    parser.add_option('-p', '--profile', action='store',
                      default=None,
                      dest='profile',
                      help='Bcfg2 System Profile',)
    parser.add_option('-u', '--url', action='store',
            default=None,
            dest='url',
            help='Puppet/Bcfg2 Server (Normally Found via RLMTools)')
    parser.add_option('-i', '--init', action='store',
            default=None,
            dest='init',
            help='Puppet/Bcfg2 Command Incantation (Normally via RLMTools)')
    parser.add_option('-d', '--dept', action='store',
            default=None,
            dest='dept',
            help='Host\'s Department string (Must Match RLMTools)')
    parser.add_option('-s', '--session', action='store',
            default='',
            dest='session',
            help='RLMTools Initial Registration Hash')

    return parser.parse_args()


def go_bcfg2(server, options):
    subs = {}

    if options.password is not None:
        subs['password'] = options.password

    if options.profile is None:
        print "You did not specify a Bcfg2 profile."
        arch = os.uname()[4]
        dist = client.getRPMDist()
        if len(arch) == 4 and arch[0] == "i" and arch[2:4] == "86":
            arch = 'i386'
        subs['profile'] = 'realmlinux-%s-%s' % (dist, arch)
        print "Assuming profile: %s" % subs['profile']
    else:
        subs['profile'] = options.profile

    if options.url is not None:
        subs['url'] = options.url

    if options.init is not None:
        subs['init'] = options.init

    # Get dept into from RLMTools
    err, rlminfo = xmlrpc.doRPC(server.getBcfg2Bootstrap, uuid, sig)
    if err > 0:
        rlminfo = {}
        logger.warning('ncsubootstrap could not grab bcfg2 info from RLMTools')
        logger.warning('Error code %s' % err)
        print "An error occured communicating with RLMTools.  Trying"
        print "Bcfg2 bootstrap based on defaults and command line options."

    # Sanitize Bootstrap info (remove multiple values)
    for key in rlminfo.keys():
        s = rlminfo[key].split('\n')[0]
        rlminfo[key] = s.strip()

    rlminfo.update(subs)
    rlminfo['uuid'] = uuid
    if 'url' not in rlminfo:
        print "WARNING: Using default Bcfg2 Repository URL: %s" % bcfg2_url
        rlminfo['url'] = bcfg2_url
    if 'init' not in rlminfo:
        print "WARNING: Using default command line template: %s" % bcfg2_init
        rlminfo['init'] = bcfg2_init
    if 'password' not in rlminfo:
        print "WARNING: Using default Bcfg2 password"
        rlminfo['password'] = 'foobar'

    cmd = rlminfo['init'] % rlminfo

    logger.info("Invoking ncsubootstrap.py to boot strap Bcfg2")
    
    os.system(cmd)


def go_puppet(server, options):
    # subs must include: fqdn, uuid, dept, url for default init string
    # fingerprint: /usr/bin/puppet agent --fingerprint

    subs = {}
    subs['fqdn'] = socket.gethostname()
    subs['uuid'] = uuid
    depts = dept_search_list(options.dept)

    if options.init is not None:
        subs['init'] = options.init
    else:
        subs['init'] = puppet_init

    if options.url is not None:
        subs['url'] = options.url
    else:
        subs['url'] = puppet_url

    ret = 1
    while len(depts) > 0 and ret & 1 == 1:
        # Running puppet through all of the possible environments until
        # the error/failure bit is not set.  We go from specific to least
        # specific
        subs['dept'] = depts.pop()
        print "Running: %s" % subs['init'] % subs

        ret = os.system(subs['init'] % subs)

    if len(depts) == 0:
        print "ERROR: Puppet bootstrap failure...giving up"
        logger.error("Puppet bootstrap failure...giving up")
        sys.exit(1)

    # what's our key's fingerprint? -- we do this the old way
    # to be compatible with earlier version os python
    fd = os.popen("/usr/bin/puppet agent --fingerprint", "r")
    fingerprint = fd.read().strip()
    fd.close()

    # Make the XMLRPC call to request cert signing
    err = xmlrpc.doRPC(server.signCert, uuid, sig, fingerprint)
    if err > 0:
        print "ERROR: Could not get Puppet Certificate signed, error # %s" \
                % err
        logger.error("Could not get Puppet Certificate signed, error # %s" \
                % err)
        sys.exit(1)

    # We should have our cert signed now, do the actual first config run
    print "Running: %s" % subs['init'] % subs
    ret = os.system(subs['init'] % subs)
    if ret & 1 == 1:
        print "ERROR: Final Puppet run failed"
        logger.error("Final Puppet run failed")
        sys.exit(1)


def main():
    global logger
    (options, args) = parse_cmd()

    URL = clientconf.initConfig(options.configfile)
    logger = logging.getLogger("rlmclient")
    server = xmlrpc.setupServer(URL)

    if os.getuid() != 0:
        print "You must be the root user to run this tool."
        sys.exit(1)

    if options.puppet == options.bcfg2:
        print "You must specify one CM tool to manage your system."
        logger.error("Incorrect invocation of ncsubootstrap")
        sys.exit(1)

    if options.dept is None:
        options.dept = client.getDepartment()

    # Check registration / don't require "ncsuclient" be run prior
    if not client.isRegistered(server):
        if client.doRegister(server, options.session) != 0:
            sys.exit(1)

    if options.bcfg2:
        go_bcfg2(server, options)
    if options.puppet:
        go_puppet(server, options)


if __name__ == "__main__":
    main()

