# webksCron.py -- Cron job to handle webks directories in Liquid Dragon
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

import optparse
import os.path

import afs.fs
import afs.acl

from webKickstart.configtools import Configuration as webKSConfig

import rlmtools.configDragon as configDragon
import rlmtools.miscServer as miscServer
from rlmtools.constants import defaultConfFiles

def fsla(path):
    # fs la <path>
    if not afs.fs.inafs(path):
        return None

    ret = []
    acls = afs.acl.ACL.retrieve(path)
    # Ignore negative ACLs for now
    for i in acls.pos.keys():
        perm = str(afs.acl.showRights(acls.pos[i]))
        ret.append((i, perm))

    return ret

def watchWKS(config):
    """Make a map of current WebKickstart directories to departments."""

    m = miscServer.MiscServer()
    webksPath = webKSConfig(config.webks_dir).hosts
    print "To read webkickstart dirs: %s" % webksPath

    for subdir in os.listdir(webksPath):
        abspath = os.path.join(webksPath, subdir)
        print "Working on: %s" % abspath
        if not os.path.isdir(abspath):
            continue

        print "   Department: %s" % subdir
        # If this doesn't match a dept it will be None - what we want
        dept_id = m.getDeptIDNoCreate(subdir)
        m.insertWebKSDir(abspath, dept_id)

        acls = fsla(abspath)
        if acls is None:
            continue

        for i in acls: print "   %s: %s" % i

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)
    watchWKS(configDragon.config)

if __name__ == "__main__":
    main()

