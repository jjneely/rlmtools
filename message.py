#!/usr/bin/python
#
# RealmLinux Manager -- client code
# Copyright (C) 2004 - 2007 NC State University
# Written by Jack Neely <jjneely@pams.ncsu.edu>
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

import os
import sha
import pickle
import base64
import os.path

from xmlrpc import doRPC

class Message(object):

    def __init__(self):
        self.data = {}
        self.sum = None

    def _setCheckSum(self):
        # dicts are unordered so we need to impose some order to checksum
        keys = self.data.keys()
        keys.sort()
        s = ""
        for key in keys:
            s = "%s%s:%s\n" % (s, key, self.data[key])
        self.sum = sha.new(s).hexdigest()

    def save(self):
        # Possibly raises IOError
        if not self.data.has_key('timestamp'):
            self.setTimeStamp()
        if self.sum == None:
            self._setCheckSum()

        filename = os.path.join(mqueue, self.sum)
        blob = pickle.dumps(self.data)
        fd = open(filename, 'w')
        fd.write(blob)
        fd.close()

    def send(self, server, text, sig):
        ret = doRPC(server.message, text, sig, self.data)
        return ret

    def remove(self):
        if self.sum != None:
            filename = os.path.join(mqueue, self.sum)
            try:
                os.unlink(filename)
            except (IOError, OSError):
                pass

    def load(self, filename):
        # Possibly raises IOError
        fd = open(filename)
        blob = fd.read()
        fd.close()
        self.data = pickle.loads(blob)
        self._setCheckSum()
        if self.sum != os.path.basename(filename):
            print "ERROR: Checksum does not equal filename."
            print "Checksum: %s" % self.sum
            print "Filename: %s" % filename

    def setType(self, t):
        self.sum = None
        self.data['type'] = t

    def setSuccess(self, bool):
        self.sum = None
        self.data['success'] = bool

    def setTimeStamp(self):
        self.sum = None
        self.data['timestamp'] = time.time()

    def setMessage(self, data):
        self.sum = None
        blob = base64.encodestring(data)
        self.data['data'] = blob

    def getTimeStamp(self):
        if self.data.has_key('timestamp'):
            return self.data['timestamp']
        else:
            return None

