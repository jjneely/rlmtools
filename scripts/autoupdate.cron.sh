#!/bin/bash
#
# autoupdate.cron.sh - Force Up2Date to run nightly at least
#
# Copyright 2004 - 2006 NC State University
# Written by Jack Neely <jjneely@pams.ncsu.edu>
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

SUBSYS=/var/lock/subsys/autoupdate

if [ ! -f $SUBSYS ] ; then
    # we're not chkconfig'd on...exit
    exit 0
fi

# We do all the actual work and sleeping in a function so that we
# can fork off this process and return so that the reset of the
# normal crons run in a timely fashion.  Otherwise the sleep here
# delays all cron script processed after this one.
newprocess() {
# Sleep to offset load on servers
sleep `perl -e 'print (int(rand(180))*60) . "\n";'`

FILE=`/bin/mktemp /tmp/autoupdate.XXXXXXXX`

if [ -x /usr/sbin/up2date ] ; then
    /usr/sbin/up2date --nox -u > $FILE 2>&1
elif [ -x /usr/bin/yum ] ; then
    /usr/bin/yum -y update > $FILE 2>&1
else
    echo "RLMTools is unable to locate the Up2date or Yum package" >  $FILE
    echo "managers and cannot apply security errata to this machine." >> $FILE
    echo "This is a serious condition and must be fixed as soon as"   >> $FILE
    echo "possible.  If you need assistance please open a ticket by"  >> $FILE
    echo "sending an email to linux@help.ncsu.edu."                   >> $FILE 
    # Use the error handling below
    false
fi

if [ "$?" -gt 0 ] ; then
    # There was an error -- tell somebody

    if [ -x /usr/bin/ncsureport ] ; then
        /usr/bin/ncsureport --service updates --fail --message $FILE
    elif [ -x /usr/bin/mutt ] ; then
        HOST=`/bin/hostname`
        /bin/cat $FILE | /usr/bin/mutt -s "${HOST} Up2date Failure" linuxroot@lists.ncsu.edu
    fi

    # This will at least get to root on the machine
    /bin/cat $FILE

else
    # Report update succeded

    [ -x /usr/bin/ncsureport ] && \
       /usr/bin/ncsureport --service updates --ok --message $FILE

fi

rm -f $FILE
}

# Fork off the update job
newprocess &

