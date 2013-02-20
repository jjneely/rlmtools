#!/bin/bash

RLMTOOLS=/usr/share/rlmtools/server

python $RLMTOOLS/graphsCron.py
python $RLMTOOLS/PTSCron.py
python $RLMTOOLS/puppetCron.py
python $RLMTOOLS/rhnCron.py
python $RLMTOOLS/webksCron.py

