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
    weekTime = 168 * 3600
    # 4*336 = 1 month (28 days)
    monthTime = 4 * weekTime
    # 12*336 = 6 months (28 * 6)
    halfYearTime = 12 * weekTime
    # 52*336 = 1 year (364 days)
    yearTime = 52 * weekTime
    # 156*336 = 3 years
    threeYearTime = 156 * weekTime

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
        self.graphs = 'graphs/'
        self.hosts  = 'hosts/'
        self.misc   = 'global/'

        for dir in [self.dir, self.graphs, self.hosts, self.misc]:
            path = os.path.isabs(dir) and dir or os.path.join(self.dir, dir)
            try:
                if not os.path.exists(path):
                    os.mkdir(path)
                if not os.access(path, os.W_OK):
                    raise StandardError("RLMTools needs write access to %s" \
                                        % path)
            except IOError:
                raise StandardError("RLMTools could not create %s" % dir)

    def time(self):
        return int(time.time())

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

            list = self.stats.getRRALocations('version', None, v['version'])
            if len(list) == 0:
                path = os.path.join(self.misc, self.hash(v['version']))
                self.stats.setRRALocation('version', None, v['version'], path)
            else:
                path = list[0]['path']

            if not os.path.isabs(path):
                path = os.path.join(self.dir, path)
            if not os.path.exists(path):
                os.system("rrdtool create %s -s 1800 %s %s" % \
                          (path, self.versionDef, self.rraDef))

            os.system("rrdtool update %s N:%s" % (path, v['count']))

    def goMaster(self):
        masterList = self.stats.getRRALocations('master', None, None)
        # Made sure we are in the DB proper
        if len(masterList) > 0:
            if len(masterList) > 1: 
                log.warning("RRDGraphs: Multiple entries for the master RRA!")
            master = masterList[0]['path']
        else:
            master = os.path.join(self.misc, self.hash('master'))
            self.stats.setRRALocation('master', None, None, master)

        fields = [
                  self.stats.getTotal(),
                  self.stats.getSupported(),
                  self.stats.getUnsupported(),
                  self.stats.getActiveClients(),
                  self.stats.getWebKickstarting(),
                  self.stats.getProblems(),
                  self.stats.getNotUpdating(),
                 ]

        if not os.path.isabs(master):
            master = os.path.join(self.dir, master)
        if not os.path.exists(master):
            os.system("rrdtool create %s -s 1800 %s %s" % (master, 
                                                           self.masterDef,
                                                           self.rraDef))
        
        os.system("rrdtool update %s N:%s" % (master, 
                  ":".join([ str(s) for s in fields ])))

    def graphMaster(self):
        masterList = self.stats.getRRALocations('master', None, None)
        if len(masterList) == 0:
            return
        if os.path.isabs(masterList[0]['path']):
            path = masterList[0]['path']
        else:
            path = os.path.join(self.dir, masterList[0]['path'])
        dest = os.path.join(self.dir, self.graphs, 'master.png')
        
        grdef = """DEF:total=%(file)s:total:AVERAGE \
                DEF:support=%(file)s:support:AVERAGE \
                DEF:nonsupport=%(file)s:nonsupport:AVERAGE \
                DEF:checkin=%(file)s:checkin:AVERAGE \
                DEF:webkickstart=%(file)s:webkickstart:AVERAGE \
                DEF:problems=%(file)s:problems:AVERAGE \
                DEF:noupdates=%(file)s:noupdates:AVERAGE \
                'LINE:total#FF0000:Total Clients' \
                'LINE:support#4D18E4:Supported Clients' \
                'LINE:nonsupport#CC3118:Unsupported Clients' \
                'LINE:checkin#B415C7:Active Clients' \
                'LINE:webkickstart#CC7016:Web Kickstarting' \
                'LINE:problems#1598C3:Clients with Problems' \
                'LINE:noupdates#C9B215:Clients Not Updating' \
                """ % {'file':path}

        cmd = "%s -s -%s -t 'Liquid Dragon Stats' -v Clients %s" % \
                (dest, self.weekTime, grdef)
        os.system("rrdtool graph %s > /dev/null 2>&1" % cmd)

def main():
    graphs = RRDGraphs()
    graphs.goMaster()
    graphs.goVersions()
    graphs.graphMaster()


if __name__ == "__main__":
    main()
