#!/usr/bin/python

# __init__.py - Initialize the RLMTools webapp
# Copyright 2012 NC State University
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

import configDragon
import constants

from flask import Flask

# Global configuration for RLMTools
config = None

app = Flask(__name__)

def __init():
    global config
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=constants.defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    parser.add_option("-a", "--auth", action="store", default=None,
                      dest="auth", 
                      help="The webapp will pretend you are this user.")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)

    # Load up the webapp module
    config = configDragon.config

    # Handle testing harness authN
    if options.auth is not None:
        rlmtools.config.vars['auth'] = ["", False]
        rlmtools.config.auth = options.auth

    # Logging: we currently use our own logging setup
    # and if we tell Flask to use it, Flask wipes out its handlers
    # as it re-creates its logger.  So we add our existing Handlers to
    # the Flask logger
    if not app.debug:
        log = logging.getLogger("xmlrpc")
        for h in log.handlers:
            app.logger.addHandler(h)

app.before_first_request(__init)

# Modules exposing views must be imported below
import rlmtools.webapp
import rlmtools.webks
import rlmtools.webadmin
import rlmtools.webperms
import rlmtools.webacl
import rlmtools.API     # XMLRPC API

