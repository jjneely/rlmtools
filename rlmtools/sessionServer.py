#!/usr/bin/python
#
# sessions.py - DB interface
#
# Copyright 2005 Jack Neely <jjneely@gmail.com>
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

# create table sessions (
#     session_id     INTEGER PRIMARY KEY auto_increment,
#     sid            varchar(255) unique not null,
#     createtime     double not null,
#     timeout        double not null,
#     data           text,
#
#     KEY `session_idx` (`sid`)
# );

import time
import logging
import server

log = logging.getLogger("xmlrpc")

class SessionServer(server.Server):

    def load(self, sid):
        q = """select createtime, timeout, data from sessions where
               sid = %s"""

        self.cursor.execute(q, (sid,))
        if self.cursor.rowcount == 0:
            return None

        r = self.cursor.fetchone()
        return r[0], r[1], r[2]
        
    def delete(self, sid):
        q = """delete from sessions where sid = %s"""

        if self.load(sid) is None:
            # Session doesn't exist
            return
        
        self.cursor.execute(q, (sid,))
        self.conn.commit()
        
    def save(self, sid, cTime, timeOut, data):
        self.delete(sid)

        q = """insert into sessions (sid, createtime, timeout, data) 
               values (%s, %s, %s, %s)"""

        self.cursor.execute(q, (sid, cTime, timeOut, data))
        self.conn.commit()

    def clean(self, delta=3600):
        """Remove old sessions from database.  For safety only delete
           sessions where timeout + delta < time.time()"""

        t = time.time() - delta
        q = """delete from sessions where timeout < %s"""

        self.cursor.execute(q, (t,))
        self.conn.commit()

