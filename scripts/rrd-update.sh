#!/bin/bash

RLMTOOLS=/usr/share/rlmtools/server

python $RLMTOOLS/graphsCron.py
python $RLMTOOLS/PTSCron.py
python $RLMTOOLS/puppetCron.py
python $RLMTOOLS/webksCron.py

# rhnCron takes a while now, it needs to run only a couple times a day
#python $RLMTOOLS/rhnCron.py


