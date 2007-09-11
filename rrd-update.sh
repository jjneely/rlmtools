#!/bin/bash

RLMTOOLS=/afs/unity/web/l/linux/secure/xmlrpc

export PYTHONPATH=$RLMTOOLS

python $RLMTOOLS/rlmtools/graphsCron.py

