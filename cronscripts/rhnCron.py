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
import pwd
import getpass

from webKickstart.configtools import Configuration as webKSConfig

import rlmtools.configDragon as configDragon
import rlmtools.permServer as permServer
from rlmtools.constants import defaultConfFiles
from rlmtools.hesiod import Hesiod

hes = Hesiod()

def isDisabled(user):
    """Return True if the given user does not exist in LDAP or is disabled."""
    groups = hes.accessGroups(user)
    if len(groups) == 0:
        return True
    if 'krb_disable' in groups:
        return True

    return False

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

def watchRHNUsers(m, server, session):
    """Identify and store folks configured as an RHN Orgizational Admin
       or higher privleged role.

       Also disable expired NCSU accounts as we grok that information 
       here as well."""

    log = logging.getLogger('xmlrpc')
    data = server.user.listUsers(session)
    users = [ i['login'] for i in data if i['enabled'] ]
    rhnProtectedUsers = m.getRHNProtectedUsers()
    realmUsers = {}
    errors = 0

    for i in users:
        try:
            pwd.getpwnam(i)
            realmUsers[i] = not isDisabled(i)
        except KeyError:
            # User does not exist in the realm at all or
            #   error talking to LDAP
            errors = errors + 1
            realmUsers[i] = False

    if not os.path.exists("/var/local/disable-rhn-users-mass-disable"):
        if errors > len(users) * 0.1:  # Abort if we nuke more than 10% of RHN
            print "WARNING: Too many errors looking up realm accounts.  Not "
            print "   disabling any RHN accounts!"
            log.error("WARNING: Too many errors looking up realm accounts. Not disabling any RHN accounts!")
            sys.exit(255)

    for i in users:
        roles = server.user.listRoles(session, i)
        if 'org_admin' in roles and i not in rhnProtectedUsers:
            m.addRHNProtectedUser(i)
            continue

        if i not in rhnProtectedUsers and not realmUsers[i]:
            try:
                print "DISABLING RHN ACCOUNT: %s" % i
                if os.path.exists("/var/local/disable-rhn-users"):
                    server.user.disable(session, i)
                else:
                    print "   Disable aborted!  Holodeck Safeties ON"
            except Exception, e:
                print "   Disable aborted! ERROR: %s" % str(e)

def watchRHN(config):
    """Make a map of current WebKickstart directories to departments."""

    log = logging.getLogger('xmlrpc')
    log.info("Running watchRHN job...")
    m = permServer.PermServer()

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
    watchRHNUsers(m, server, session)

    try:
        server.auth.logout(session)
    except Exception, e:
        # If we blow up during logout just ignore it
        pass

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

