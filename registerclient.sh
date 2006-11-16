#/bin/bash
#
#    registerclient.sh - Wrapper script to register Realm Linux clients
#    Copyright 2004, 2006 NC State University
#    Written by Jack Neely <jjneely@pams.ncsu.edu>
#
#    SDG
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

/usr/bin/Wait

FILE=`mktemp /tmp/regXXXXXX`
/usr/lib/rlmtools/client.py > $FILE 2>&1 

OUTPUT=`cat $FILE`

if [ "$OUTPUT" != "" ] ; then

    # Email the output to some one useful instead of root

    if [ -x /usr/bin/mutt ] ; then
        # check for the send command -- should be installed
        HOST=`/bin/hostname`
        /bin/cat $FILE | /usr/bin/mutt -s "${HOST}: NCSU XMLRPC" jjneely@ncsu.edu
    else
        # no mutt...let root know
        cat $FILE
    fi

fi

rm -f $FILE

