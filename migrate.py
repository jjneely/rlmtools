#!/usr/bin/python
#
# migrate.py - Migrate Realm Linux to Satellite
# Copyright 2005 NC State University
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

# This script modified to help with RHN Proxy - RHN Satellite migration
# 2005/3/17
#
# Edited to reregister clients against the new Satellite
# 2005/05/17

import sys

sys.path.append("/usr/share/rhn/up2date_client")
sys.path.append("/afs/eos/project/realmlinux/py-modules")

from config import ConfigFile
import xmlrpclib
import os
import ezPyCrypto

publicKey = "/etc/sysconfig/RLKeys/rkhost.pub"
privateKey = "/etc/sysconfig/RLKeys/rkhost.priv"
publicRLKey = "/etc/sysconfig/RLKeys/realmlinux.pub"


class rcModule(object):

    moduleName = "Up2Date Configuration"

    runPriority = 7

    fileRequires = ['/usr/share/rhn/up2date_client/config.py',
                    '/etc/sysconfig/rhn/up2date']

    runOnce = 1

    NCSUDefault = {
        'serverURL':        'https://rhn.linux.ncsu.edu/XMLRPC',
        'noSSLServerURL':   'http://rhn.linux.ncsu.edu/XMLRPC',
#        'pkgSkipList':      ["kernel*", "openafs*"],
        'sslCACert':        '/usr/share/rhn/RHN-ORG-TRUSTED-SSL-CERT'}

    forceConfig = 0
    
    def run(self, debug=0):
        if ConfigFile == None:
            return 

        conf = ConfigFile('/etc/sysconfig/rhn/up2date')
        
        # Have we done this before?  Don't wax an admin's changes
        if conf['serverURL'] == self.NCSUDefault['serverURL']:
            # We are already configured
            if self.forceConfig == 0:
                return

        for key in self.NCSUDefault.keys():
            conf[key] = self.NCSUDefault[key]

        conf.save()


def getLocalKey():
    "Return an ezPyCrypto keypair for this local host."
    
    if not os.access(privateKey, os.R_OK):
        print "Error importing keys for checkin."
        return None
    
    fd = open(privateKey)
    keyText = fd.read()
    fd.close()

    key = ezPyCrypto.key()
    key.importKey(keyText)

    return key


server = xmlrpclib.ServerProxy(
                  "https://secure.linux.ncsu.edu/xmlrpc/handler.py")

keypair = getLocalKey()
if keypair == None:
    print "Unsupported workstation.  Using default key."
    rhnkey = "6ed40e5c831bd8a8d706f0abe8f44f09"
else:
    pubKey = keypair.exportKey()
    sig = keypair.signString(pubKey)
    rhnkey = server.getActivationKey(pubKey, sig)

print "Using RHN Activation Key %s" % rhnkey

# Fix the up2date configuration file
mod = rcModule()
mod.forceConfig = 1
mod.run()

ret = os.system("/usr/sbin/rhnreg_ks --force --activationkey %s" % rhnkey)
print "rhnreg_ks returned %s" % ret

