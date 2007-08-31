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

def __subs(src, dict):
    return [ line % dict for line in src ]

rrdColors = [
        ('#EA644A',  '#CC3118'), # red
        ('#48C4EC',  '#1598C3'), # blue
        ('#EC9D48',  '#CC7016'), # orage
        ('#54EC48',  '#24BC14'), # green
        ('#ECD748',  '#C9B215'), # yellow
        ('#DE48EC',  '#B415C7'), # indigo
        ('#7648EC',  '#4D18E4'), # violet
       ]

timeZones= ['3d', '1w', '4w', '12w', '52w', '156w']

masterDef = [
        "DS:total:GAUGE:3600:0:U",
        "DS:support:GAUGE:3600:0:U",
        "DS:nonsupport:GAUGE:3600:0:U",
        "DS:checkin:GAUGE:3600:0:U",
        "DS:webkickstart:GAUGE:3600:0:U",
        "DS:problems:GAUGE:3600:0:U",
        "DS:noupdates:GAUGE:3600:0:U",
        ]

versionDef = ["DS:version:GAUGE:3600:0:U"]

rraDef = [
        "RRA:AVERAGE:0.5:1:336",
        "RRA:AVERAGE:0.5:4:336",
        "RRA:AVERAGE:0.5:12:336",
        "RRA:AVERAGE:0.5:52:336",
        "RRA:AVERAGE:0.5:156:336",
        ]

usageDef = [
        "DS:users:GAUGE:600:0:U",
        "RRA:AVERAGE:0.5:1:600",
        "RRA:AVERAGE:0.5:6:384",
        "RRA:AVERAGE:0.5:24:840",
        "RRA:AVERAGE:0.5:144:730",
        "RRA:AVERAGE:0.5:288:1095",
        ]

def masterGraph(d):
    src = [
    "DEF:support=%(file)s:support:AVERAGE",
    "DEF:nonsupport=%(file)s:nonsupport:AVERAGE",
    "DEF:webkickstart=%(file)s:webkickstart:AVERAGE",
    "DEF:checkin=%(file)s:checkin:AVERAGE",
    "CDEF:Ln1=support,support,UNKN,IF",
    "CDEF:Ln2=nonsupport,support,nonsupport,+,UNKN,IF",
    "CDEF:Ln3=webkickstart,support,nonsupport,webkickstart,+,+,UNKN,IF",
    "AREA:support#54EC48:Supported Clients:STACK",
    "AREA:nonsupport#EA644A:Unsupported Clients:STACK",
    "AREA:webkickstart#ECD748:Web Kickstarting:STACK",
    "LINE:Ln1#24BC14",
    "LINE:Ln2#CC3118",
    "LINE:Ln3#C9B215",
    "LINE2:checkin#1598C3:Active Clients",
    ]

    return __subs(src, d)

def problemsGraph(d):
    src = [
        "DEF:noupdates=%(file)s:noupdates:AVERAGE",
        "DEF:problems=%(file)s:problems:AVERAGE",
        "DEF:total=%(file)s:total:AVERAGE",
        "LINE2:noupdates#CC3118:Clients Not Updating",
        "LINE2:problems#C9B215:Clients With Problems",
        "LINE2:total#24BC14:Total Clients",
        ]

    return __subs(src, d)

