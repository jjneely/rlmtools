# puppetCron.py -- Cron job to handle puppet directories in Liquid Dragon
#
# Copyright 2013 NC State University
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

import logging
import optparse
import os.path

import rlmtools.configDragon as configDragon
import rlmtools.permServer as permServer
from rlmtools.constants import defaultConfFiles

PuppetPath = None

def watchPuppet(config):
    """Make a map of current Puppet directories to departments."""

    log = logging.getLogger('xmlrpc')
    log.info("Running watchPuppet job...")
    m = permServer.PermServer()
    scrubbedPaths = []
    if not os.path.exists(PuppetPath):
        log.warning("Puppet directory %s not found. Aborting." \
                % PuppetPath)
        return

    for subdir in os.listdir(PuppetPath):
        abspath = os.path.join(PuppetPath, subdir)
        log.debug("watchPuppet: Working on: %s" % abspath)
        if not os.path.isdir(abspath):
            continue

        scrubbedPaths.append(abspath)
        # If this doesn't match a dept it will be None - what we want
        dept_id = m.getDeptIDNoCreate(subdir)
        m.insertPuppetDir(abspath, dept_id)

    m.cleanPuppetDirs(scrubbedPaths)

def main():
    global PuppetPath
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)
    PuppetPath = configDragon.config.puppet_dir

    watchPuppet(configDragon.config)

if __name__ == "__main__":
    main()

