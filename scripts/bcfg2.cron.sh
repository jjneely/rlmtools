#!/bin/bash
#
# bcfg2.cron.sh - Run Bcfg2, the Configuration Management Tool
#
# Copyright 2009 NC State University
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

# Default to being enabled
# Turn off in /etc/sysconfig/bcfg2 (which is also managed by Bcfg2)
BCFG2_ENABLED=1
BCFG2_OPTIONS="-qv"
BCFG2_BIN=/usr/sbin/bcfg2
BCFG2_CFG=/etc/bcfg2.conf

# Read the configuration from /etc/sysconfig/bcfg2
[ -e /etc/sysconfig/bcfg2 ] && . /etc/sysconfig/bcfg2

# We do all the actual work and sleeping in a function so that we
# can fork off this process and return so that the reset of the
# normal crons run in a timely fashion.  Otherwise the sleep here
# delays all cron script processed after this one.
newprocess() {
    # Sleep to offset load on servers
    sleep `perl -e 'print (int(rand(40))*60) . "\n";'`
    
    FILE=`/bin/mktemp /tmp/bcfg2.XXXXXXXX`

    # Check that configuration and executable exists
    if [ -x ${BCFG2_BIN} -a -e ${BCFG2_CFG} ] ; then
        ${BCFG2_BIN} -C ${BCFG2_CFG} ${BCFG2_OPTIONS} > $FILE 2>&1
    else
        echo "RLMTools is unable to locate Bcfg2, the configuration " >  $FILE
        echo "manager, and cannot apply configuration on this machine." >> $FILE
        echo "This is a serious condition and must be fixed as soon as"   >> $FILE
        echo "possible.  If you need assistance please open a ticket by"  >> $FILE
        echo "sending an email to linux@help.ncsu.edu."                   >> $FILE 
        # Use the error handling below
        false
    fi

    if [ "$?" -gt 0 ] ; then
        # There was an error -- tell somebody

        if [ -x /usr/bin/ncsureport ] ; then
            /usr/bin/ncsureport --service bcfg2 --fail --message $FILE
        elif [ -x /usr/bin/mutt ] ; then
            HOST=`/bin/hostname`
            /bin/cat $FILE | /usr/bin/mutt -s "${HOST} Bcfg2 Failure" \
                                           linuxroot@lists.ncsu.edu
        fi

        # This will at least get to root on the machine
        /bin/cat $FILE

    else
        # Report update succeded

        [ -x /usr/bin/ncsureport ] && \
        /usr/bin/ncsureport --service bcfg2 --ok --message $FILE

    fi

    rm -f $FILE
}

# Fork off the job
[ "$BCFG2_ENABLED" == "1" ] && newprocess &

