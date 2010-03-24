#!/bin/bash

# Run this script in cron with stdout redirected to /dev/null
# Important errors are written to stderr

MASTERREPOS=/afs/bp/system/config/linux-kickstart/bcfg2
LOCALREPOS=/srv/bcfg2

if [ ! -x /usr/bin/git ] ; then
    echo "Git not installed.  Bailing."
    exit 1
fi

if [ ! -d $LOCALREPOS ] ; then
    mkdir -p $LOCALREPOS
fi

# This bit of magic with the root directory makes it first in the list
REPOS="root $(ls --hide root $MASTERREPOS)"
for r in $REPOS; do
    if [ ! -d $MASTERREPOS/$r ] ; then continue ; fi
    if [ -d $LOCALREPOS/$r ] ; then
        cd $LOCALREPOS/$r
        git pull
    elif [ -e $LOCALREPOS/$r ] ; then
        echo "ERROR: Non-directory $LOCALREPOS/$r already exists..." > /dev/stderr
        continue
    else
        cd $LOCALREPOS
        git clone $MASTERREPOS/$r $r
    fi

    if [ -e $LOCALREPOS/$r/bcfg2.pid ] ; then
        PID=`cat $LOCALREPOS/$r/bcfg2.pid`
    else
        PID="X"
    fi

    if [ ! -e $LOCALREPOS/$r/bcfg2.conf ] ; then
        # No config file
        echo "$LOCALREPOS/$r lacks bcfg2.conf" > /dev/stderr
        continue
    fi

    if [ "$PID" != "X" -a -e /proc/$PID ] ; then
        if [ $LOCALREPOS/$r/bcfg2.conf -nt $LOCALREPOS/$r/bcfg2.pid ] ; then
            # The bcfg2.conf file is newer than the running bcfg2-server
            # process.  We need to get it to reload the bcfg2.conf file
            echo "Killing $r bcfg2-server for restart"
            kill -9 $PID
            rm -f $LOCALREPOS/$r/bcfg2.pid
            # -9 Is needed for some weird kernel interaction with RHEL5
            # Do not continue, drop through to where we start the bcfg2-server
        else
            # We are done...bcfg2-server is running
            continue
        fi
    fi

    # Start up a bcfg2 server for this repo
    echo "Starting Bcfg2 server for $LOCALREPOS/$r"
    /usr/sbin/bcfg2-server -D $LOCALREPOS/$r/bcfg2.pid \
                           -C $LOCALREPOS/$r/bcfg2.conf
    if [ "$?" != "0" ] ; then
        echo "ERROR: Failed to start bcfg2-server for $LOCALREPOS/$r" > /dev/stderr
    fi
done

