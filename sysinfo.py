#!/usr/bin/python
#
# sysinfo.py - Report basic system information to RLM
# Copyright (C) 2006 NC State University
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

import os
import sys

def vendor():
    print "Vendor:"
    # Attempt to diplay DMI information
    sys.path.append("/usr/share/rhn/up2date_client")
    
    try:
        import hardware
    except ImportError, e:
        print "Could not load hardware module."
        print
        return

    info = hardware.read_dmi()
    for key in info.keys():
        print "   %s: %s" % (key, info[key])
    print

def report():
    print "Uptime:"
    print os.popen("uptime").read()

    print "Uname:"
    print os.popen("uname -a").read()

    print "SELinux:"
    if os.access("/etc/sysconfig/selinux", os.R_OK):
        for line in open("/etc/sysconfig/selinux").readlines():
            if line.startswith("SELINUX"):
                print line.strip()
    else:
        print "N/A"

    print
    print "Network:"
    print os.popen("/sbin/ifconfig").read()

def main():
    vendor()
    report()


if __name__ == "__main__":
    main()
