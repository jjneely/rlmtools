#!/usr/bin/python
#
# RealmLinux Manager -- Cron job to generate graphs/stats
# Copyright (C) 2007 NC State University
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

# This script is designed to be run every 30 minutes from cron.
# It should have read/write access to the rrd_dir as stored in the
# database.  You probably want to run this as apache so it has the 
# same rights as the web app portion which also may generate graphs
# and such.

# The rrd_dir has the following inside:
# <rrd_dir>
#   |-> hosts/       - Directory containing RRDs for hosts
#   |-> global/      - Directory containing RRDs for the global system
#   | |-> master.rra - RRD file containing general statistics
#   | |-> <version>  - RRDs for deployed versions
#   |-> graphs/      - Directory containing dynamically generated graphs

import sys
import sha
import logging
import os
import os.path

from datetime     import datetime, timedelta
from configDragon import config
from statsServer  import StatsServer

log = logging.getLogger("xmlrpc")

class RRDGraphs(object):

    # Sampling ever 30 minutes.
    # 1*336 = 1 week
    # 4*336 = 1 month (28 days)
    # 12*336 = 6 months (28 * 6)
    # 52*336 = 1 year (364 days)
    # 156*336 = 3 years
    masterDef = """DS:total:GAUGE:3600:0:U   \
                   DS:support:GAUGE:3600:0:U \
                   DS:nonsupport:GAUGE:3600:0:U \
                   DS:checkin:GAUGE:3600:0:U \
                   DS:webkickstart:GAUGE:3600:0:U \
                   DS:problems:GAUGE:3600:0:U \
                   DS:noupdates:GAUGE:3600:0:U"""

    versionDef ="""DS:version:GAUGE:3600:0:U"""

    rraDef =    """RRA:AVERAGE:0.5:1:336 \
                   RRA:AVERAGE:0.5:4:336 \
                   RRA:AVERAGE:0.5:12:336 \
                   RRA:AVERAGE:0.5:52:336 \
                   RRA:AVERAGE:0.5:156:336"""

    def __init__(self):
        self.stats = StatsServer()

        self.dir    = config.rrd_dir
        self.graphs = os.path.join(self.dir, 'graphs/')
        self.hosts  = os.path.join(self.dir, 'hosts/')
        self.misc   = os.path.join(self.dir, 'global/')
        self.master = os.path.join(self.misc, self.hash('master'))

        for dir in [self.dir, self.graphs, self.hosts, self.misc]:
            try:
                if not os.path.exists(dir):
                    os.mkdir(dir)
                if not os.access(dir, os.W_OK):
                    raise StandardError("RLMTools needs write access to %s" \
                                        % dir)
            except IOError:
                raise StandardError("RLMTools could not create %s" % dir)

    def time(self):
        return str(int(time.time()))

    def hash(self, s):
        return sha.new(s).hexdigest() + ".rra"

    def goVersions(self):
        data = self.stats.getVersions()

        for v in data:
            # Get rid of bad data
            if len(v['version']) < 1:
                continue
            if v['version'].find(' ') > -1:
                continue
            if v['version'].find('\t') > -1:
                continue

            path = os.path.join(self.misc, self.hash(v['version']))
            if not os.path.exists(path):
                os.system("rrdtool create %s -s 1800 %s %s" % \
                          (path, self.versionDef, self.rraDef))

            os.system("rrdtool update %s N:%s" % (path, v['count']))

    def goMaster(self):
        fields = [
                  self.stats.getTotal(),
                  self.stats.getSupported(),
                  self.stats.getUnsupported(),
                  self.stats.getActiveClients(),
                  self.stats.getWebKickstarting(),
                  self.stats.getProblems(),
                  self.stats.getNotUpdating(),
                 ]

        if not os.path.exists(self.master):
            os.system("rrdtool create %s -s 1800 %s %s" % (self.master, 
                                                           self.masterDef,
                                                           self.rraDef))
        
        os.system("rrdtool update %s N:%s" % (self.master, 
                  ":".join([ str(s) for s in fields ])))

def main():
    graphs = RRDGraphs()
    graphs.goMaster()
    graphs.goVersions()


if __name__ == "__main__":
    main()
