#!/usr/bin/python
#
# dbcron.py -- Cron job to maintain DB
# Copyright (C) 2004 - 2006 NC State University
# Written by Jack Neely <jjneely@pncsu.edu>
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

import socket
from rlmtools import server

def cleanDB(cursor):
    # SQL to delete machines no longer checking in
    sql1 = """delete from realmlinux where 
              TO_DAYS(NOW()) - TO_DAYS(lastcheck) > 90;"""
    
    # SQL to delete machines that installed but never registered
    sql2 = """delete from realmlinux where
              TO_DAYS(NOW()) - TO_DAYS(installdate) > 30 and 
              lastcheck is NULL;"""

    cursor.execute(sql1)
    cursor.execute(sql2)


def main():
    s = server.Server(socket.getfqdn())
    s.cleanDB()

if __name__ == "__main__":
    main()
    
