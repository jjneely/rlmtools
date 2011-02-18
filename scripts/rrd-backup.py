#!/usr/bin/python
#
# rrd-backup.py - Backup/restore a directory tree of RRA files
# Copyright (C) 2011 NC State University
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

import os.path
import os
import sys
import optparse

def err(s): sys.stderr.write("%s\n" % s)

def sanity_check_dir(dir):
    # The path must be a directory and must exist
    dir = os.path.normpath(dir)
    if dir.endswith('/'):
        dir = dir[:-1]
    if not os.path.exists(dir):
        err("Path \"%s\" does not exist. Refusing to continue." % dir)
        sys.exit(2)
    if not os.path.isdir(dir):
        err("Path \"%s\" is not a directory. Refusing to continue." % dir)
        sys.exit(2)

    return dir

def run(source, target, restore=False):
    # If restore is Faluse a backup job is run.  Otherwise a restore job.
    def callback(arg, dirname, filenames):
        if dirname.startswith(source):
            path = dirname[len(source):]
        else:
            err("While traversing %s we found ourselves in %s" \
                    % (source, dirname))
            err("I don't like this and I'm going home.")
            sys.exit(3)
        if path.startswith('/'):
            path = path[1:]
        newdir = os.path.join(target, path)
        if not os.path.exists(newdir):
            os.mkdir(newdir)

        for file in filenames:
            print "Examining: %s" % file
            if not os.path.isfile(os.path.join(dirname, file)): continue
            if restore and (not file.endswith(".xml")): continue
            if not restore and (not file.endswith(".rra")): continue
            # Okay, we have the target file, dump or restore it
            if restore:
                newfile = os.path.join(newdir, file[:-4] + ".rra")
            else:
                newfile = os.path.join(newdir, file[:-4] + ".xml")
            if os.path.exists(newfile):
                err("Previous Backup/Restore?  %s already exists." % newfile)
                sys.exit(3)
            print "Creating %s..." % newfile
            if restore:
                cmd = "/usr/bin/rrdtool restore %s %s"
            else:
                cmd = "/usr/bin/rrdtool dump %s %s"

            if os.system(cmd % (os.path.join(dirname, file), newfile)) != 0:
                err("Error executing: %s -- continuing" % cmd)

    os.path.walk(source, callback, None)

def main():
    usage = "Usage: %prog [-b|-r] source-directory target-directory"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-b", "--backup", action="store_true",
                      default=False,
                      dest="backup",
                      help="Perform backup")
    parser.add_option("-r", "--restore", action="store_true",
                      default=False,
                      dest="restore",
                      help="Perform restore")

    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_usage()
        sys.exit(1)
    if options.backup and options.restore:
        err("Error: You cannot do both a backup and restore")
        sys.exit(1)
    if not options.backup and not options.restore:
        err("Error: You must chose to do either a backup or restore.")
        sys.exit(1)

    # Let's try to make the target directory if that appears to be requested
    if not os.path.exists(args[1]):
        head, tail = os.path.split(args[1])
        if tail != '' and os.path.exists(head):
            os.mkdir(os.path.join(head, tail))

    target = sanity_check_dir(args[1])
    source = sanity_check_dir(args[0])

    run(source, target, options.restore)


if __name__ == "__main__":
    main()

