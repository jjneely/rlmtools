# rhnCron.py -- Cron job to handle RHN requests
#
# Copyright 2011 NC State University
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

import xmlrpclib
import logging
import optparse
import os.path
import sys
import getpass

from webKickstart.configtools import Configuration as webKSConfig

import rlmtools.configDragon as configDragon
import rlmtools.miscServer as miscServer
from rlmtools.constants import defaultConfFiles

def getRHN(rhnurl, user, passwd):
    server = xmlrpclib.ServerProxy(rhnurl)
    session = server.auth.login(user, passwd, 3600)

    return server, session

def diffAndInsert(m, rhnGroups, knownGroups):
    "Diffing algorythm to insert new groups"

    rhnKeys = rhnGroups.keys()
    rhnKeys.sort()
    knownKeys = knownGroups.keys()
    knownKeys.sort()

    i = 0
    while i < len(rhnKeys):
        if len(knownKeys) <= i or knownKeys[i] > rhnKeys[i]:
            m.insertRHNGroup(rhnGroups[rhnKeys[i]]['name'], rhnKeys[i], None)
            # Keep our index numbers intact
            knownKeys.insert(i, rhnKeys[i]) 
            i = i + 1
        elif knownKeys[i] < rhnKeys[i]:
            m.rmRHNGroup(knownGroups[knownKeys[i]]['rg_id'])
            del knownKeys[i]            # Keep our index numbers intact
        elif knownKeys[i] == rhnKeys[i]:
            i = i + 1
    while len(knownKeys) > len(rhnKeys):
        m.rmRHNGroup(knownGroups[knownKeys[i]]['rg_id'])
        del knownKeys[i]                # Keep our index numbers intact

def watchRHN(config):
    """Make a map of current WebKickstart directories to departments."""

    log = logging.getLogger('xmlrpc')
    log.info("Running watchRHN job...")
    m = miscServer.MiscServer()

    server, session = getRHN(config.rhnurl, config.rhnuser, config.rhnpasswd)
    groups = server.systemgroup.listAllGroups(session)

    # Build a dict hashed on the RHN Group ID
    rhnGroups = {}
    for g in groups:
        rhnGroups[g['id']] = g

    # Parse our known groups similarly
    knownGroups = {}
    for g in m.getRHNGroups():
        knownGroups[g['rhng_id']] = g

    diffAndInsert(m, rhnGroups, knownGroups)

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)
    watchRHN(configDragon.config)

if __name__ == "__main__":
    main()

