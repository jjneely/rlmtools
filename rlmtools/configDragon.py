#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2003, 2005, 2006, 2007 NC State University
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

import sys
import logging
import server
import ConfigParser

from constants import defaultConfFiles
from logging.handlers import WatchedFileHandler

config_files = None   # The files we look in for configuration
config = None         # The main configuration object
log = logging.getLogger("xmlrpc")
init_logging = True

# Format:
# config option -> (help string, isIntType)
requiredConfig = {
        'default_admin': ["First user with admin access permission.", False],
        'webks_dir': ["Directory where the Web-Kickstart configs live.", False],
        'privatekey': ["Filename for the private key.", False],
        'publickey': ["Filename for the public key.",   False],
        'key_directory': ["Directory clients public keys appear.", False],
        'secret': ["Set an authentication secret for the XMLRPC API.", False],
        'defaultkey': ["Set default blowfish key for root password crypts.", False],
        'rrd_dir': ["Directory round robin databases will live.", False],
        'rhnurl': ["URL to the RHN XMLRPC API Interface.", False],
        'rhnuser': ["RHN administrative user to issue commands.", False],
        'rhnpasswd': ["Password for RHN admin user.", False],
        }

def initLogging():
    global init_logging
    if not init_logging: return

    parser = ConfigParser.ConfigParser()
    parser.read(config_files)

    if parser.sections() == []:
        raise StandardError("Error reading config file to locate database.")
    try:
        logfile = parser.get('main', 'logfile')
        level = int(parser.get('main', 'log_level'))
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        raise StandardError("Database config file missing sections/options.")

    logger = logging.getLogger("xmlrpc")

    try:
        handler = WatchedFileHandler(logfile)
        fileError = None
    except IOError, e:
        # XXX: cannot open file, deal with it
        handler = logging.StreamHandler()
        fileError = str(e)

    # Time format: Jun 24 10:16:54
    formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s',
            '%b %2d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    logger.info("Liquid Dragon: logging initialized.")
    if fileError is not None:
        logger.warning("IOError accessing logfile: %s" % fileError)

    init_logging = False

class Parser(ConfigParser.ConfigParser):

    def get(self, section, option, default):
        """
        Override ConfigParser.get: If the request option is not in the
        config file then return the value of default rather than raise
        an exception.  We still raise exceptions on missing sections.
        """
        try:
            return ConfigParser.ConfigParser.get(self, section, option)
        except ConfigParser.NoOptionError:
            return default

class ConfigDragon(server.Server):

    # Same format as requiredConfig.  The help string probably wont be used.
    # This defines any internal bits we want to store.
    vars = {
           }

    def removeValue(self, key, holdCommit=False):
        q = "delete from configvalues where variable = %s"
        self.cursor.execute(q, (key,))
        if not holdCommit:
            self.conn.commit()

    def setValue(self, key, value):
        q = "insert into configvalues (variable, value) values (%s, %s)"

        # Database stores values in a TEXT field
        value = str(value)

        if key in requiredConfig.keys() + self.vars.keys():
            self.removeValue(key, holdCommit=True)
            self.cursor.execute(q, (key, value))
            self.conn.commit()
        else:
            raise StandardError("Illegal configuration parameter: %s" % key)

    def __getattr__(self, key):
        q = "select value from configvalues where variable = %s"

        if key in requiredConfig.keys() + self.vars.keys():
            self.cursor.execute(q, (key,))
            if self.cursor.rowcount > 0:
                if key in requiredConfig.keys() and requiredConfig[key][1]:
                    return int(self.cursor.fetchone()[0])
                elif key in self.vars.keys() and self.vars[key][1]:
                    return int(self.cursor.fetchone()[0])
                else:
                    return self.cursor.fetchone()[0]
            else:
                return None
        else:
            raise AttributeError("Configuration has no '%s' parameter" % key)

    def verifyConfiguration(self):
        "Return True for valid configurations."

        for key in requiredConfig.keys() + self.vars.keys():
            if getattr(self, key) == None:
                return False
        return True


def initConfig(files):
    global config_files, config

    if config is not None:
        return # we are already setup

    config_files = files
    server.config_files = files
    initLogging()
    config = ConfigDragon()
    if not config.verifyConfiguration():
        raise StandardError("RLMTools does not have a complete configuration "
                            "in the database.")

def checkConfig(config):
    for key in requiredConfig.keys():
        value = getattr(config, key)
        if key in ['privatekey', 'secret', 'defaultkey', 'rhnpasswd'] and value != None:
            print "%s: <Sensitive data not printed>" % key
        else:
            print "%s: %s" % (key, value)

    print
    if config.verifyConfiguration():
        print "Configuration is valid."
    else:
        print "Configuration is incomplete.  Please add the missing values."

def main():
    import optparse
    global config_files, config

    parser = optparse.OptionParser()
    for key in requiredConfig.keys():
        parser.add_option("--set"+key, action="store", default=None,
                      dest=key, 
                      help=requiredConfig[key][0])

    parser.add_option("--check", action="store_true", default=False,
                      dest="check", 
                      help="Check and verify the stored configuration.")
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    opts, args = parser.parse_args(sys.argv[1:])

    print "Liquid Dragon Configuration Tool.\n"
    print "Licensed under the GNU General Public License version 2.0 or, at"
    print "your option, any greater version."
    print

    config_files = opts.configfile
    server.config_files = opts.configfile
    initLogging()
    config = ConfigDragon()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    if opts.check:
        checkConfig(config)
        sys.exit(0)

    for key in requiredConfig.keys():
        value = getattr(opts, key)
        if key in ['privatekey', 'publickey'] and value != None:
            value = open(value).read()
        if value != None:
            config.setValue(key, value)


if __name__ == "__main__":
    main()

