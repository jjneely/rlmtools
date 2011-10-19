#!/usr/bin/python

# hesiod.py - Module to get Hesion information from LDAP
# Copyright 2011 Jack Neely
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

import ldap
import sys

# Where is the LDAP tree
URI = 'ldap://ldap.ncsu.edu'

##  User groups 
#
LDAP_USER_BASE='ou=accounts,dc=ncsu,dc=edu'
LDAP_USER_FILTER='(&(objectClass=posixAccount)(uid=%s))'
LDAP_USER_ATTR='memberNisNetgroup'

LDAP_HOST_BASE='ou=hosts,dc=ncsu,dc=edu'
##  Host deny groups                                                          
#                                                                             
LDAP_HOST_DENY_FILTER='(&(objectClass=ncsuHost)(cn=%s))'
LDAP_HOST_DENY_ATTR='ncsuDenyNetgroup'

##  Host allow groups                                                         
#                                                                             
LDAP_HOST_ALLOW_FILTER='(&(objectClass=ncsuHost)(cn=%s))'
LDAP_HOST_ALLOW_ATTR='ncsuAllowNetgroup'

class Hesiod(object):

    def __init__(self):
        self.conn = ldap.initialize(URI)
        self.conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

    def getLDAPAttr(self, base, filter, attr):
        id = self.conn.search(base, ldap.SCOPE_ONELEVEL,
                              filter, [attr])
        r_type, r_data = self.conn.result(id)
        if r_type != ldap.RES_SEARCH_RESULT:
            raise StandardError("Got error %s from LDAP" % r_type)

        if len(r_data) < 1:
            return []

        # Assume looking up a specific user will give 1 DN back
        attributes = r_data[0][1].values()
        if len(attributes) > 0 and type(attributes[0]) == type([]):
            return attributes[0]
        elif len(attributes) > 0:
            return attributes
        else:
            # I wonder if we get here
            return []

    def stripGroupList(self, list):
        ret = []

        for dn in list:
            i = dn.find('=')
            j = dn.find(',')
            if i < j and i > -1 and j > -1:
                ret.append(dn[i+1:j])

        return ret

    def accessDNs(self, user):
        return self.getLDAPAttr(LDAP_USER_BASE, LDAP_USER_FILTER % user, 
                                LDAP_USER_ATTR)

    def accessGroups(self, user):
        dns = self.accessDNs(user)
        return self.stripGroupList(dns)

    def allowGroups(self, host):
        groups = self.getLDAPAttr(LDAP_HOST_BASE, 
                                  LDAP_HOST_ALLOW_FILTER % host,
                                  LDAP_HOST_ALLOW_ATTR)
        return self.stripGroupList(groups)

    def denyGroups(self, host):
        groups = self.getLDAPAttr(LDAP_HOST_BASE, 
                                  LDAP_HOST_DENY_FILTER % host,
                                  LDAP_HOST_DENY_ATTR)
        return self.stripGroupList(groups)

    def isUserAllowed(self, user, host):
        unixgroups = set(self.accessGroups(user))
        deny = set(self.denyGroups(host))
        allow = set(self.allowGroups(host))

        if len(unixgroups & deny) > 0:
            return False
        elif len(unixgroups & allow) > 0:
            return True
        else:
            return False
        

def main():
    if len(sys.argv) < 3:
        print "%s <uid> <host>"
        print "Prints access information about a user and also the optional host."
        sys.exit(1)

    user = sys.argv[1]
    if len(sys.argv) > 2:
        host = sys.argv[2]
    else:
        host = None

    l = Hesiod()
    print "accessDNs:"
    print l.accessDNs(sys.argv[1])
    print
    print "accessGroups:"
    print l.accessGroups(sys.argv[1])
    print
    print "allowGroups"
    print l.allowGroups(host)
    print
    print "denyGroups"
    print l.denyGroups(host)
    print
    print "Is Usder Allowed?"
    print l.isUserAllowed(user, host)

if __name__ == "__main__":
    main()


