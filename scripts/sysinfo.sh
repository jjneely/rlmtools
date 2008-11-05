#!/bin/bash

# Report system information to RLM

python /usr/share/rlmtools/sysinfo.py | \
    /usr/bin/ncsureport --service sysinfo --ok --message -

