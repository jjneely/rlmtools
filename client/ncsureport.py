#!/usr/bin/python
# Realm Linux Management - Queue a message to upload to central server
# Copyright (C) 2004 - 2007 NC State University
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

import optparse
import sys

from message import Message
import clientconf

def doReport():
    usage = """Realm Linux Management report tool.  Licensed under the 
GNU General Public License.
ncsureport --service < --ok | --fail > --message <file>"""
    parser = optparse.OptionParser(usage)
    parser.add_option("-s", "--service", action="store", default=None,
                     dest="service", help="Message/service type to send.")
    parser.add_option("-o", "--ok", action="store_true", default=None,
                     dest="ok", help="Service is a success.")
    parser.add_option("-f", "--fail", action="store_true", default=None,
                     dest="fail", help="Service is a failure.")
    parser.add_option("-m", "--message", action="store", default=False,
                     dest="message", help="Filename or '-' of message to send.")
    parser.add_option("-C", "--configfile", action="store",
                      default=defaultConfFiles,
                      dest="configfile",
                      help="Configuration file")

    opts, args = parser.parse_args(sys.argv[1:])
    clientconf.initConfig(opts.configfile)

    if opts.ok == None and opts.fail == None:
        parser.print_help()
        return

    if opts.service == None:
        parser.print_help()
        return

    success = opts.ok == True
    if opts.message == "-":
        fd = sys.stdin
        blob = fd.read()
    elif opts.message == False:
        blob = ""
    else:
        try:
            fd = open(opts.message)
            blob = fd.read()
        except IOError, e:
            print "Count not open file: %s" % opts.message
            return

    m = Message()
    m.setType(opts.service)
    m.setSuccess(success)
    m.setMessage(blob)
    try:
        m.save()
    except (OSError, IOError), e:
        print "There was an error queuing your message: %s" % str(e)
        print "Message will not be sent."


if __name__ == "__main__":
    doReport()

