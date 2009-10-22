#!/bin/bash

MASTERREPOS=/afs/bp/system/config/linux-kickstart/bcfg2
LOCALREPOS=/tmp/bcfg2repos

if [ ! -x /usr/bin/git ] ; then
    echo "Git not installed.  Bailing."
    exit 1
fi

if [ ! -d $LOCALREPOS ] ; then
    mkdir -p $LOCALREPOS
fi

for r in `ls $MASTERREPOS`; do
    if [ -d $LOCALREPOS/$r ] ; then
        cd $LOCALREPOS/$r
        git pull
    elif [ -e $LOCALREPOS/$r ] ; then
        echo "ERROR: Non-directory $LOCALREPOS/$r already exists..."
    else
        cd $LOCALREPOS
        git clone $MASTERREPOS/$r $r
    fi
done

