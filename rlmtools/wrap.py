#!/usr/bin/python
#
# wrap.py -- Support NCSU's WRAP authentication under mod_python 
# Copyright (C) 2005, 2012 NC State University
# Written by Jack Neely <jjneely@ncsu.edu>
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

import re
import struct
import base64
import time
import logging
import Crypto.PublicKey.RSA as RSA
import Crypto.Util.number as number
#import Crypto.Util.asn1 as asn1 

log = logging.getLogger("xmlrpc")

# Encrypted with NCSU's WRAP key
KNOWN_GOOD = 'S6zbm08iaJx97Q7POLKGMXvOPTTGQwu+O9wSJ/zVzMTfy8+9CcXBKc2Wsz7ag7Ru1VvQsz8HULep1xxQY7SkZid6eEH5Y1r5WkYWaQQGLgR9X1aPu3i/9BkAm7WeH8+c'

# XXX: Unless we upgrade to python-crypto >= 2.2 we can only use the
# raw version of the WRAP public key.

class WRAPError(Exception): pass

class WRAPCookie(object):

    def __init__(self, cookie, keyFile=None):
        if type(cookie) == type(""):
            self.cookie = cookie
        elif isinstance(cookie, dict):
            if not cookie.has_key('WRAP16'):
                # Odd...no WRAP cookie
                self.cookie = None
            else:
                self.cookie = cookie['WRAP16']
            
        else:
            raise WRAPError("Cookie argument not a known type.")

        self.userID = None
        self.affiliation = None
        self.expiration = None
        self.address = None
        self.onProxy = None
        
        if self.cookie is None:
            return

        if keyFile:
            self.pubKey(keyFile)
            self.parse()
        else:
            raise WRAPError("No keyFile provided.")

    def pubKey(self, file):
        fd = open(file)
        self.size = int(fd.readline().strip())

        l = fd.readline().strip()
        blob = base64.decodestring(l)
        self.__n = number.bytes_to_long(blob)

        l = fd.readline().strip()
        blob = base64.decodestring(l)
        self.__d = number.bytes_to_long(blob)

        self.rsa = RSA.RSAobj()
        self.rsa.n = self.__n
        self.rsa.d = self.__d

    def _RSAPaddingCheck(self, clear):
        # This removes the padding on the strings from the RSA encryption
        # This also verifies that the string decrypted propperly
        # The 0xff can be variable so the regex seems best...
        regex = re.compile("^\x01\xff*\x00")
        m = regex.search(clear)
        if m:
            return m.string[m.end():]
        else:
            return None

    def parse(self):

        # Step 1: Decode string
        try:
            blob = base64.decodestring(self.cookie)
        except Exception, e:
            # Failed to decode
            log.info("Failed to decode BASE64 WRAP cookie")
            return False

        blob = number.bytes_to_long(blob)

        # Step 2: Decrypt
        try:
            clear = self.rsa.decrypt(blob)
        except Exception, e:
            log.info("Failed to decrypt WRAP cookie")
            return False

        clear = number.long_to_bytes(clear)
        
        # Step 3: Verify and remove padding
        cstruct = self._RSAPaddingCheck(clear)
        if cstruct:
            try:
                tuple = struct.unpack("16s20s10s15s1s", cstruct)
                self.userID = tuple[0].partition('\0')[0]
                self.affiliation = tuple[1].partition('\0')[0]
                self.expiration = tuple[2].partition('\0')[0]
                self.address = tuple[3].partition('\0')[0]
                self.onProxy = tuple[4].partition('\0')[0]

                return True
            except Exception, e:
                # We failed to unpack the cookie binary data
                log.info("Failed to unpack binary data from WRAP cookie")
                return False

    def isExpired(self):
        if self.expiration is None:
            return True
        if int(self.expiration) < time.time():
            return True

        return False

    def isValid(self):
        if self.userID is None:
            return False
        return not self.isExpired()


def main():
    # testing
    c = WRAPCookie(KNOWN_GOOD, '/etc/httpd/conf/wrap16.raw')
    print c.userID
    print c.affiliation
    print c.expiration
    print c.address
    print c.onProxy
    print "Expired: %s" % c.isExpired()
    print "Valid  : %s" % c.isValid()

if __name__ == "__main__":
    main()

