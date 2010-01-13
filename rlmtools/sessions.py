#!/usr/bin/python
#
# sessions.py - Manage sessions for a in a generic manner for both a web
#    interface and an XMLRPC interface
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

import sha
import time
import random
import cPickle as pickle
import sessionServer as sessions

class Session(dict):

    def __init__(self, sid=None, lifetime=3600, secret=None):
        """Create a new session.  If sid is not None attempt to load that
           session from the store."""

        dict.__init__(self)
        self.db = sessions.SessionServer()
        self.lifetime = lifetime

        if sid == None:
            # create new object
            self.__new(secret)
            return
        
        try:
            self.createTime, self.timeOut, data = self.db.load(sid)
        except TypeError:
            # unpack error means we returned None, session doesn't exist
            self.__new(secret)
            return
        
        if not self.isValid():
            self.__new(secret)
        else:
            d = pickle.loads(data)

            for key in d.keys():
                self[key] = d[key]

            self.is_new = False
            self.sid = sid


    def __new(self, secret):
        self.createTime = time.time()
        self.timeOut = self.createTime + self.lifetime
        s = "Liquid-Dragon-%s-%s" % (str(random.random()), str(secret))
        self.sid = sha.new(s).hexdigest()
        self.is_new = True
        
                                                        
    def isNew(self):
        return self.is_new


    def isValid(self):
        return self.timeOut >= time.time()

    
    def invalidate(self):
        self.setTimeOut(0)


    def setTimeOut(self, secs):
        """Set the time out in seconds since session creation."""

        self.timeOut = secs


    def save(self):
        """Save session to db and clean db"""

        self.db.clean()

        data = pickle.dumps(dict(self))
        self.db.save(self.sid, self.createTime, self.timeOut, data)

