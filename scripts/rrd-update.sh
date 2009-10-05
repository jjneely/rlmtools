#!/bin/bash

RLMTOOLS=`python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"`

python $RLMTOOLS/rlmtools/graphsCron.py
python $RLMTOOLS/rlmtools/PTSCron.py

