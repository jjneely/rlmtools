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
import time
import rrdtool
import optparse

from datetime     import datetime, timedelta
from statsServer  import StatsServer
from rrdconstants import *
from constants    import defaultConfFiles

import configDragon

log = logging.getLogger("xmlrpc")

class RRDGraphs(object):

    def __init__(self):
        self.stats = StatsServer()

        self.dir    = configDragon.config.rrd_dir
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
                log.info("Creating version RRD: %s" % path)
                cli = [path, '-s', '1800'] + versionDef + rraDef
                rrdtool.create(*cli)

            rrdtool.update(path, "N:%s" % v['count'])

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
            log.info("Creating master RRD: %s" % master)
            cli = [master, '-s', '1800'] + masterDef + rraDef
            rrdtool.create(*cli)
        
        cli = [master, "N:%s" % ":".join([ str(s) for s in fields ])]
        rrdtool.update(*cli)

    def getHostRRA(self, host_id):
        "Return the abolute path the the host RRA."

        path = self.stats.getRRALocations('usage', host_id, None)
        if path == []:
            s = "usage %s" % host_id
            rra = self.hash(s)
            dir = rra[0:2]
            path = os.path.join(self.hosts, dir, rra)
            self.stats.setRRALocation('usage', host_id, None, path)
        else:
            path = path[0]['path']

        abspath = os.path.join(self.dir, path)
        if not os.path.exists(os.path.dirname(abspath)):
            try:
                os.mkdir(os.path.dirname(abspath))
            except IOError:
                raise StandardError("RLMTools: cound not create %s" % \
                                    os.path.dirname(abspath))
        if not os.path.exists(abspath):
            # RRDs are created with start time of 03/14/2007 to start
            # before any potential data may have been generated.
            log.info("Creating host RRD: %s" % abspath)
            cli = [abspath, '-s', '300', '-b', '1173844800'] + usageDef
            rrdtool.create(*cli)

        return abspath

    def handleUsage(self):
        """Pulls the usage information out of the db and into the RRDs."""
        
        increment = 300 # 300 seconds or 5 minutes
        hosts = self.stats.getSyncStates()
        for host in hosts:
            host_id = host['host_id']
            maxSafe = host['timestamp']
            usage = self.stats.getUsageEvents(host_id, maxSafe)
            pdps = {}
            updates = []
            log.debug("HandleUsage(): Working on host_id %s, maxSafe = %s events = %s" % (host_id, maxSafe, len(usage)))

            for event in usage:
                # Everthing needs to be in seconds sence the epoch now
                stamp = int(time.mktime(event['timestamp'].timetuple()))
                start = stamp - event['length']
                if start <= 1173844800:
                    # The earlest any login event can be
                    log.warning("Host ID %s submitted bad usage event." \
                                % host_id)
                    log.warning("Time range %s - %s" % \
                                (time.ctime(start), time.ctime(stamp)))
                    continue

                i = start + (increment - (start % increment))
                while i <= stamp:
                    if pdps.has_key(i):
                        pdps[i] = pdps[i] + 1
                    else:
                        pdps[i] = 1
                    i = i + increment

            path = self.getHostRRA(host_id)
            lastUpdate = rrdtool.last(path)
            keys = pdps.keys()
            keys.sort()
            for i in keys:
                # Build the RRDTool update command
                if i <= lastUpdate:
                    # DATA LOSS!!!
                    # We cannot force data into the rrdb because we have
                    # data already in it that's newer
                    log.warning("Dropping PDP %s:%s for host id %s" % \
                                (i, pdps[i], host_id))
                else:
                    updates.append("%s:%s" % (i, pdps[i]))

            if len(updates) > 0:
                updates.insert(0, path)
                rrdtool.update(*updates)

            self.stats.clearUsageEvents(host_id, maxSafe)

    def graph(self, dest, defs, *args):
        cmd = "rrdtool graph %s-%s.png -s -%s %s %s > /dev/null 2>&1"

        if len(defs) == 0:
            log.info("No data to graph for %s" % dest)
            return
        for zone in timeZones:
            cli = ["%s-%s.png" % (dest, zone),
                   "-s", "-%s" % zone, ] + list(args) + defs
            rrdtool.graph(*cli)

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
        self.graph(dest1, masterGraph({'file':path}), "-t",
                   "Liquid Dragon Totals", "-v", "Clients")
        self.graph(dest2, problemsGraph({'file':path}), "-t",
                   "Liquid Dragon Problem Clients", "-v", "Clients")

    def graphVersions(self):
        list = self.stats.getRRALocations('version', None, None)
        defs = []
        actions = []
        c = 0
        for v in list:
            c = c + 1
            if not os.path.isabs(v['path']):
                path = os.path.join(self.dir, v['path'])
            else:
                path = v['path']

            if not os.path.exists(path):
                # The database knows about versions that no longer exist
                log.info("Creating version RRD: %s" % path)
                cli = [path, '-s', '1800'] + versionDef + rraDef
                rrdtool.create(*cli)
            
            reflist = ['v%s,' % str(i+1) for i in range(c) ]
            rpn = "+," * (c - 1) + "UNKN,IF"
            d = {'c':c, 'file':path, 'reflist':''.join(reflist), 'rpn':rpn,
                 'light':rrdColors[c % 7][0], 'label':v['label']}

            defs.append("DEF:v%(c)s=%(file)s:version:AVERAGE" % d)
            defs.append("CDEF:ln%(c)s=v%(c)s,%(reflist)s%(rpn)s" % d)
            actions.append("AREA:v%(c)s%(light)s:%(label)s:STACK" % d)
            
        for i in range(len(list)):
            actions.append("LINE1:ln%s%s" % (i+1, rrdColors[(i+1) % 7][1]))

        self.graph(os.path.join(self.dir, self.graphs, 'versions'),
                defs + actions, '-l', '0',
                "-t", "Realm Linux Versions", "-v", "Clients", "-h", "200")

    def __usageHelper(self, list, domain):
        defs = []
        actions = []
        c = 0

        for rra in list:
            if os.path.isabs(rra['path']):
                path = rra['path']
            else:
                path = os.path.join(self.dir, rra['path'])

            if not os.path.exists(path):
                log.debug("Request for non-existant RRA: %s" % path)
                continue

            defs.append("DEF:v%s=%s:users:AVERAGE" % (c, path))
            actions.append("AREA:v%s%s::STACK" % (c, rrdColors[3][0]))
            c = c + 1

        self.graph(os.path.join(self.dir, self.graphs, domain),
                   defs+actions, '-l', '0', '-t', 'Realm Linux Usage',
                   '-v', 'People', '-e', '-1d')

    def graphMasterUsage(self):
        list = self.stats.getRRALocations('usage')
        self.__usageHelper(list, 'usage')

    def graphDeptUsage(self):
        for dept in self.stats.getDepartments():
            list = self.stats.getRRALocations('usage', dept=dept)
            self.__usageHelper(list, 'usage@%s' % dept)

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases
    configDragon.initConfig(options.configfile)

    log.info("Running RRDGraphs cron job...")
    graphs = RRDGraphs()
    graphs.goMaster()
    graphs.goVersions()
    graphs.graphMaster()
    graphs.graphVersions()
    graphs.handleUsage()
    graphs.graphMasterUsage()
    graphs.graphDeptUsage()

if __name__ == "__main__":
    main()

