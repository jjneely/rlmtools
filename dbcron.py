#!/usr/bin/python
#
#     RealmLinux Manager -- Cron job to maintain DB
#     Copyright (C) 2004 NC State University
#     Written by Jack Neely <jjneely@pams.ncsu.edu>
#
#     SDG
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys
import MySQLdb
import ConfigParser

testmode = 0

if testmode:
    configFile = "/home/slack/projects/tmp/keys/testing.conf"
else:
    configFile = "/afs/eos/www/linux/configs/web-kickstart.conf"


def getConn():
    # get MySQL information
    global configFile
    cnf = ConfigParser.ConfigParser()
    cnf.read(configFile)
		
    dbhost = cnf.get('db', 'host')
    dbuser = cnf.get('db', 'user')
    dbpasswd = cnf.get('db', 'passwd')
    db = cnf.get('db', 'db')
        
    # Open a MySQL connection and cursor
    conn = MySQLdb.connect(host=dbhost, user=dbuser,
                                passwd=dbpasswd, db=db)

    return conn


def cleanDB(cursor):
    # SQL to delete machines no longer checking in
    sql1 = """delete from realmlinux where 
              TO_DAYS(NOW()) - TO_DAYS(lastcheck) > 30;"""
    
    # SQL to delete machines that installed but never registered
    sql2 = """delete from realmlinux where
              TO_DAYS(NOW()) - TO_DAYS(installdate) > 30 and 
              lastcheck is NULL;"""

    cursor.execute(sql1)
    cursor.execute(sql2)


def main():
    conn = getConn()
    cursor = conn.cursor()

    cleanDB(cursor)


if __name__ == "__main__":
    main()
    
