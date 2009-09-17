#!/usr/bin/python
#
# RealmLinux Manager -- Main server object
# Copyright (C) 2003, 2005, 2006, 2007 NC State University
# Written by Jack Neely <jjneely@ncsu.edu>
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

import sys
import logging
import traceback
import mysql
import ConfigParser

from datetime import datetime

log = logging.getLogger("xmlrpc")

# Holds the database class
DataBase = None

def logException():
    # even though tracing is not normally done at lower logging levels,
    # we add trace data for exceptions
    file, line, func, txt = traceback.extract_stack(None, 2)[0]
    trace = 'EXCEPTION (File: %s, Method: %s(), Line: %s): [%s]\n' % \
            (file, func, line, txt)
    log.critical(trace)

    (type, value, tb) = sys.exc_info()
    for line in traceback.format_exception(type, value, tb):
        log.critical(line.strip())

def getDBDict():
    files = ['./rlmtools.conf', '/etc/rlmtools.conf']

    parser = ConfigParser.ConfigParser()
    parser.read(files)

    if parser.sections() == []:
        raise StandardError("Error reading config file to locate database.")

    try:
        db = {}
        db['db_host'] = parser.get('db', 'host')
        db['db_user'] = parser.get('db', 'user')
        db['db_pass'] = parser.get('db', 'passwd')
        db['db_name'] = parser.get('db', 'db')
        return db
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        raise StandardError("Database config file missing sections/options.")


class Server(object):

    # Use class variables so we don't have to connect each time
    conn = None
    cursor = None

    def __init__(self):
        """Set up server and define who we are talking to...well at least
           what we are told we are talking to."""
           
        global DataBase
        if DataBase == None:
            # Init MySQL Connections
            DataBase = mysql.MysqlDB(getDBDict())

        if self.conn == None or self.cursor == None:
            # get MySQL information
            self.conn = DataBase.getConnection()
            self.cursor = DataBase.getCursor()


    # Convienance functions that are a part of each Server object

    def getDSID(self, name):
        """Returns the database ID for the given DS type for use with
           RRDTool."""

        q = "select ds_id from dstype where name = %s"
        self.cursor.execute(q, (name,))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None

    def setServiceID(self, serv):
        "Create a Service ID"

        q = "insert into service (name) values (%s)"

        sid = self.getServiceID(serv)
        if sid == None:
            self.cursor.execute(q, (serv,))
            self.conn.commit()
            return self.getServiceID(serv)
        else:
            return sid

    def getServiceID(self, serv):
        "Return the ID for this service.  None if the service doesn't exist."

        q = "select service_id from service where name = %s"
        self.cursor.execute(q, (serv,))

        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]
        else:
            return None

    def getDeptName(self, dept_id):
        q = """select name from dept where dept_id = %s"""

        self.cursor.execute(q, (dept_id,))
        result = self.cursor.fetchone()
        if result == None:
            return None
        else:
            return result[0]

    def getDeptID(self, dept):
        "Return the DB ID of this department.  Create it if needed."

        q1 = "select dept_id from dept where name = %s"
        q2 = "insert into dept (name) values (%s)"

        # Normallize the department strings
        dept = dept.replace(' ', '-').lower()
        dept = self.conn.escape_string(dept)

        self.cursor.execute(q1, (dept,))
        if self.cursor.rowcount > 0:
            return self.cursor.fetchone()[0]

        self.cursor.execute(q2, (dept,))
        self.conn.commit()

        self.cursor.execute(q1, (dept,))
        return self.cursor.fetchone()[0]

    def getHostName(self, host_id):
        q = """select hostname from realmlinux where host_id = %s"""
        self.cursor.execute(q, (host_id,))
        if self.cursor.rowcount < 1:
            return None
        else:
            return self.cursor.fetchone()[0]

    def getHostID(self, hostname):
        self.cursor.execute("""select host_id from realmlinux where
                               hostname = %s""", (hostname,))
        if self.cursor.rowcount == 0:
            log.warning("Tried to pull host_id for %s who doesn't exist" \
                        % hostname)
            return None

        return self.cursor.fetchone()[0]

    def getUuidID(self, uuid):
        self.cursor.execute("""select host_id from realmlinux where
                               uuid = %s""", (uuid,))
        if self.cursor.rowcount == 0:
            log.warning("Tried to pull host_id for %s who doesn't exist" \
                        % uuid)
            return None

        return self.cursor.fetchone()[0]

    def getHistTypeID(self, htype):
        q = "select htype_id from htype where name = %s"

        self.cursor.execute(q, (htype,))
        if self.cursor.rowcount == 0:
            log.warning("Tried to pull history type for unknown event: %s" \
                        % htype)
            return None

        return self.cursor.fetchone()[0]

    def storeHistoryEvent(self, htype, host_id, data):
        """Store a history event.
              htype - string form of history type
              host_id - affected host ID or None
              data - arbitrary string
        """

        q = """insert into history (htype_id, host_id, `timestamp`, data)
               values (%s, %s, %s, %s)"""

        data = str(data)
        htype_id = self.getHistTypeID(htype)
        if htype_id == None:
            return

        self.cursor.execute(q, (htype_id, host_id, datetime.today(), data))
        self.conn.commit()


