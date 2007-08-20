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
from rrdconstants import *

log = logging.getLogger("xmlrpc")

class RRDGraphs(object):

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
                          (path, versionDef, rraDef))

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
                                                           masterDef,
                                                           rraDef))
        
        os.system("rrdtool update %s N:%s" % (master, 
                  ":".join([ str(s) for s in fields ])))

    def handleUsage(self):
        """Pulls the usage information out of the db and into the RRDs."""

        pass

    def graph(self, dest, args, defs):
        cmd = "rrdtool graph %s-%s.png -s -%s %s %s > /dev/null 2>&1"

        for zone in timeZones:
            os.system(cmd % (dest, zone, zone, args, defs))

    def graphMaster(self):
        masterList = self.stats.getRRALocations('master', None, None)
        if len(masterList) == 0:
            return
        if os.path.isabs(masterList[0]['path']):
            path = masterList[0]['path']
        else:
            path = os.path.join(self.dir, masterList[0]['path'])
        dest1 = os.path.join(self.dir, self.graphs, 'master')
        dest2 = os.path.join(self.dir, self.graphs, 'problems')
        self.graph(dest1, "-t 'Liquid Dragon Totals' -v Clients",
                   masterGraph % {'file':path})
        self.graph(dest2, "-t 'Liquid Dragon Problem Clients' -v Clients",
                   problemsGraph % {'file':path})

    def graphVersions(self):
        list = self.stats.getRRALocations('version', None, None)
        defs = ""
        actions = ""
        c = 0
        for v in list:
            c = c + 1
            if not os.path.isabs(v['path']):
                path = os.path.join(self.dir, v['path'])
            else:
                path = v['path']
            
            reflist = ['v%s,' % str(i+1) for i in range(c) ]
            rpn = "+," * (c - 1) + "UNKN,IF"
            d = {'c':c, 'file':path, 'reflist':''.join(reflist), 'rpn':rpn,
                 'light':rrdColors[c % 7][0], 'label':v['label']}
            defs = defs + "DEF:v%(c)s=%(file)s:version:AVERAGE " % d
            defs = defs + "CDEF:ln%(c)s=v%(c)s,%(reflist)s%(rpn)s " % d
            actions = actions + "'AREA:v%(c)s%(light)s:%(label)s:STACK' " % d
            
        for i in range(len(list)):
            actions = actions + "LINE1:ln%s%s " % (i+1, rrdColors[(i+1) % 7][1])

        self.graph(os.path.join(self.dir, self.graphs, 'versions'),
                "-t 'Realm Linux Versions' -v Clients -h 200",
                   defs + actions)

def main():
    graphs = RRDGraphs()
    graphs.goMaster()
    graphs.goVersions()
    graphs.graphMaster()
    graphs.graphVersions()


if __name__ == "__main__":
    main()

