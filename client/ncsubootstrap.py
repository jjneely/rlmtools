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
import getpass
import sys
import os

from constants import *

import xmlrpc
import clientconf
import client

logger = None

uuid = client.getUUID()
dist = client.getRPMDist()
dept = client.getDepartment()

def main():
    global logger

    usage = """Realm Linux Management Bcfg2 Boot Strap Tool.
Licensed under the GNU General Public License.
ncsurename [-C configfile]"""
    parser = optparse.OptionParser(usage)
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="RLMTools Configuration file")
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
                      help='Bcfg2 Location (Normally Found via RLMTools)')
    parser.add_option('-i', '--init', action='store',
        default=None,
        dest='init',
        help='Bcfg2 Command Incantation (Normally via RLMTools)')

    (options, args) = parser.parse_args()

    URL = clientconf.initConfig(options.configfile)
    logger = logging.getLogger("rlmclient")
    server = xmlrpc.setupServer(URL)

    if os.getuid() != 0:
        print "You are not root.  Insert error message here."
        sys.exit(1)

    subs = {}

    if options.password is None:
        print "You must supply a password to authenticate to the Bcfg2"
        print "repository.  The password for the root level public repository"
        print "is: \"foobar\""
        print
        subs['password'] = getpass.getpass('Password: ')
    else:
        subs['password'] = options.password

    if options.profile is None:
        print "You did not specify a Bcfg2 profile."
        arch = os.uname()[4]
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
    err, rlminfo = xmlrpc.doRPC(server.getDeptBcfg2, dept)
    if err > 0:
        rlminfo = {}
        logger.warning('ncsubootstrap could not grab bcfg2 info from RLMTools')
        logger.warning('Error code %s' % err)
        print "An error occured communicating with RLMTools"
        if 'url' not in subs:
            print "If you specify the URL to the Bcfg2 repository"
            print "I can try to fake it."
            sys.exit(2)
        else:
            logger.warning('Trying with default bcfg2.init string')
            print "I think I have enough information to bootstrap Bcfg2 anyway"
            subs['init'] = constants.bcfg2_init

    rlminfo.update(subs)
    rlminfo['uuid'] = uuid
    cmd = rlminfo['init'] % rlminfo

    logger.info("Invoking ncsubootstrap.py to boot strap Bcfg2")
    
    os.system(cmd)


if __name__ == "__main__":
    main()

