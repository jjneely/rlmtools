#!/usr/bin/python
#
# RealmLinux Manager -- constants
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

# XMLRPC Interface
URL = "https://secure.linux.ncsu.edu/xmlrpc/handler.py"

# Locally stored keys
publicKey = "/etc/sysconfig/RLKeys/rkhost.pub"
privateKey = "/etc/sysconfig/RLKeys/rkhost.priv"
publicRLKey = "/etc/sysconfig/RLKeys/realmlinux.pub"
uuidFile = "/etc/sysconfig/RLKeys/uuid"

# Where blessings go
blessings_dir = "/afs/bp/system/config/linux-kickstart/blessings"

# Message Queue Directory
mqueue = "/var/spool/rlmqueue"

# Default locations of the config file
defaultConfFiles = ['/etc/rlmtools.conf', './rlmtools.conf']

# Default logging info
logfile = ''               # This logs to syslog
log_level = '1'            # A text represntation of an int, log level

# Default Bcfg2 Bootstrap info.  
bcfg2_init = '/usr/sbin/bcfg2 -qv -u %(uuid)s -x %(password)s -p %(profile)s -S %(url)s'
bcfg2_url = 'https://cm.linux.ncsu.edu:6000'

# Default Puppet Bootstrap info
puppet_init = '/usr/bin/puppet agent --test --certname %(fqdn)s-%(uuid)s --environment %(dept)s --server %(url)s --pluginsync --color=false'
puppet_fingerprint = '/usr/bin/puppet agent --certname %(fqdn)s-%(uuid)s --fingerprint'
puppet_url = 'puppet.linux.ncsu.edu'

