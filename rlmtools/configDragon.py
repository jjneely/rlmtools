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

config_files = ['./solaris2ks.conf', '/etc/solaris2ks.conf']
log = logging.getLogger("xmlrpc")
init_logging = True

def initLogging():
    global init_logging
    if not init_logging:
        return

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
    handler = logging.FileHandler(logfile)
    # Time format: Jun 24 10:16:54
    formatter = logging.Formatter(
            '%(asctime)s LD %(levelname)s: %(message)s',
            '%b %2d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    logger.info("Liguid Dragon: logging initialized.")

    init_logging = False

class ConfigDragon(server.Server):

    textVars = [
                'privatekey',
                'publickey',
                'key_directory',
                'secret',
                'defaultkey',
               ]

    intVars =  [
               ]

    init_logging = True

    def removeValue(self, key, holdCommit=False):
        q = "delete from configvalues where variable = %s"
        self.cursor.execute(q, (key,))
        if not holdCommit:
            self.conn.commit()

    def setValue(self, key, value):
        q = "insert into configvalues (variable, value) values (%s, %s)"

        if key in self.intVars:
            value = str(value)

        if key in self.textVars or key in self.intVars:
            self.removeValue(key, holdCommit=True)
            self.cursor.execute(q, (key, value))
            self.conn.commit()
        else:
            raise StandardError("Illegal configuration parameter: %s" % key)

    def __getattr__(self, key):
        q = "select value from configvalues where variable = %s"

        if key in self.intVars or key in self.textVars:
            self.cursor.execute(q, (key,))
            if self.cursor.rowcount > 0:
                if key in self.intVars:
                    return int(self.cursor.fetchone()[0])
                else:
                    return self.cursor.fetchone()[0]
            else:
                return None
        else:
            raise AttributeError("Configuration has no '%s' parameter" % key)

    def verifyConfiguration(self):
        "Return True for valid configurations."

        for key in self.textVars:
            if getattr(self, key) == None:
                return False

        for key in self.intVars:
            if getattr(self, key) == None:
                return False

        return True


def checkConfig(config):
    l = []
    l.extend(config.textVars)
    l.extend(config.intVars)

    for key in l:
        value = getattr(config, key)
        if key in ['privatekey', 'secret', 'defaultkey'] and value != None:
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

    config = ConfigDragon()
    parser = optparse.OptionParser()
    parser.add_option("--setprivatekey", action="store", default=None,
                      dest="setprivatekey", 
                      help="Filename for the private key.")
    parser.add_option("--setpublickey", action="store", default=None,
                      dest="setpublickey", 
                      help="Filename for the public key.")
    parser.add_option("--setkey_directory", action="store", default=None,
                      dest="setkey_directory", 
                      help="Directory clients public keys appear.")
    parser.add_option("--setsecret", action="store", default=None,
                      dest="setsecret", 
                      help="Set an authentication secret for the XMLRPC API.")
    parser.add_option("--setdefaultkey", action="store", default=None,
                      dest="setdefaultkey", 
                      help="Set default blowfish key for root password crypts.")

    parser.add_option("--check", action="store_true", default=False,
                      dest="check", 
                      help="Check and verify the stored configuration.")

    opts, args = parser.parse_args(sys.argv[1:])

    print "Liquid Dragon Configuration Tool.\n"

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    if opts.check:
        checkConfig(config)
        sys.exit(0)

    l = config.textVars + config.intVars
    for key in l:
        value = getattr(opts, "set"+key)
        if key in ['privatekey', 'publickey'] and value != None:
            value = open(value).read()
        if value != None:
            config.setValue(key, value)


if __name__ == "__main__":
    main()
else:
    if init_logging:
        initLogging()

    config = ConfigDragon()
    if not config.verifyConfiguration():
        raise StandardError("RLMTools does not have a complete configuration in the database.")

