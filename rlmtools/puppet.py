import os.path
import logging
import json

from socket import gethostname

import restclient

log = logging.getLogger("xmlrpc")

class Puppet(object):

    def __init__(self, url="https://puppet.linux.ncsu.edu:8140"):
        # This machine should be a Puppet client, find the certificates
        ssldir = "/var/lib/puppet/ssl"

        self.ca = os.path.join(ssldir, "certs/ca.pem")
        if not os.path.exists(ca):
            raise StandardError("Puppet CA certificate not found: %s" % ca)

        uuid = self.getLocalUUID()
        fqdn = gethostname()

        self.certname = "%s-%s" % (fqnd, uuid)

        self.key  = os.path.join(ssldir, "private_keys/", self.certname)
        self.cert = os.path.join(ssldir, "certs/", self.certname)

        for i in [self.key, self.cert]:
            if not os.path.exists(i):
                msg = "Puppet Certificate/Key not found: %s" % i
                raise StandardError(msg)

        self.http = restclient.RestClient(url, ca=self.ca, sslkey=self.key
                sslcrt=self.cert)

    def getLocalUUID(self):
        try:
            fd = open("/etc/sysconfig/RLKeys/uuid", "r")
            blob = fd.read()
            fd.close()
        except Exception, e:
            msg = "Could not access local UUID file: %s" % str(e)
            raise StandardError(msg)

        return blob.strip()

    

