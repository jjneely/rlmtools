#!/bin/bash
#
# rrd-backup.sh - Wrapper for backup job
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

SOURCE=/var/rlmtools
TARGET=$1

if [ -z "$TARGET" ] ; then
    echo "No taget specified on command line."
    exit 1
fi

if [ ! -d $TARGET ] ; then
    echo "Specified target must be an existing directory."
    exit 1
fi

FILENAME=rlmtools-rra-`date "+%Y-%m-%d-%H:%M"`.bz2
TMPDIR=`mktemp -d /var/tmp/rlmtools.XXXXXXXXXX`

python /usr/share/rlmtools/server/rrd-backup.py -b ${SOURCE} \
    ${TMPDIR}/rlmtools

tar cjf ${TARGET}/${FILENAME} -C ${TMPDIR} rlmtools

rm -rf ${TMPDIR}

# Should be set to 2 weeks worth of dumps, plus a small fudge factor
/usr/sbin/tmpwatch -m 340 ${TARGET}


