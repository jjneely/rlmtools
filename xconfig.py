#!/usr/bin/python
#
# config.py -- Configuration class for webKickstrart
#
# Copyright 2003-2006 NC State University
# Written by Elliot Peele <elliot@bentlogic.net>
#            Jack Neely <jjneely@pams.ncsu.edu>
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
import ConfigParser
import os
import sys
import os.path

class Configuration(ConfigParser.ConfigParser):

    init_logging = True
    
    def __init__(self, configfile=['/etc/solaris2ks.conf',
                                   './solaris2ks.conf']):
        ConfigParser.ConfigParser.__init__(self)
        
        self.cfg_file = []

        # resolve non-absoulte paths relative to the directory containing
        # the web-kickstart code.  Fixes CWD dependancies.
        if type(configfile) is not type([]):
            configfile = [configfile]
        for p in configfile:
            if not os.path.isabs(p):
                p = os.path.join(sys.path[0], p)
            self.cfg_file.append(p)

        self.read(self.cfg_file)
        if self.sections() == []:
            raise errors.AccessError("Can't access %s CWD: %s" % \
                    (self.cfg_file, os.getcwd()))

        if self.init_logging:
            self.initLogging()
            self.init_logging = False

    def getDBDict(self):
        db = {}
        db['db_host'] = self.get('db', 'host')
        db['db_user'] = self.get('db', 'user')
        db['db_pass'] = self.get('db', 'passwd')
        db['db_name'] = self.get('db', 'db')
        return db

    def _getoption(self, section, option):
        try:
            return self.get(section, option)
        except ConfigParser.NoSectionError, e:
            raise errors.ConfigError('Failed to find section: %s' % (section))
        except ConfigParser.NoOptionError, e:
            return None

    def initLogging(self):
        logger = logging.getLogger("xmlrpc")
        
        file = self.get('main', 'logfile')
        level = self.get('main', 'log_level')

        handler = logging.FileHandler(file)
        # Time format: Jun 24 10:16:54
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                      '%b %2d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(int(level))

        logger.info("XMLRPC Logging initialized.")

        self.init_logging = False
                                

# Global config
config = Configuration()

