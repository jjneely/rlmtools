#!/usr/bin/python

# A python script to help in the db migration process during the 
# testing phase

from rlmtools.adminServer import AdminServer
from rlmtools.constants import defaultConfFiles
from rlmtools import configDragon

configDragon.initConfig(defaultConfFiles)

s = AdminServer()
s._setupParents()

root = s.getDeptID('root')
for row in s.getPTSGroups():
    if row['name'] == 'admintest':
        s.setPerm(row['acl_id'], root, 7)
    if row['name'] == 'admin':
        s.setPerm(row['acl_id'], root, 7)
    if row['name'] == 'installer:common':
        s.setPerm(row['acl_id'], root, 4)

