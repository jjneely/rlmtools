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
        if not os.path.exists(self.ca):
            raise StandardError("Puppet CA certificate not found: %s" \
                    % self.ca)

        uuid = self.getLocalUUID()
        fqdn = gethostname()

        self.certname = "%s-%s" % (fqdn, uuid)
        pem = self.certname + ".pem"

        self.key  = os.path.join(ssldir, "private_keys/", pem)
        self.cert = os.path.join(ssldir, "certs/", pem)

        for i in [self.key, self.cert]:
            if not os.path.exists(i):
                msg = "Puppet Certificate/Key not found: %s" % i
                raise StandardError(msg)

        self.http = restclient.RestClient(url, ca=self.ca, sslkey=self.key,
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

    def getCertStatus(self, fqdn, uuid):
        client = "%s-%s" % (fqdn, uuid)
        r, c = self.http.get("/root/certificate_status/%s" % client,
                headers = {'Accept':'pson'})

        if r.status == 404:
            # There is no certificate
            return None
        elif r.status != 200:
            # We got an error back
            log.error("Puppet API Error: %s - %s" % (r.reason, c))
            raise StandardError("Puppet API Error: %s - %s" % (r.reason, c))

        # Return the dict from Puppet: keys: name, state, fingerprint
        return json.loads(c)

    def signCert(self, fqdn, uuid, fingerprint):
        meta = self.getCertStatus(fqdn, uuid)
        if meta == None:
            log.warning("Puppet API: Asked to sign non-existant cert for %s" \
                    % uuid)
            return False

        if meta['fingerprint'] != fingerprint:
            log.warning("Puppet API: Cert fingerprint missmatch for %s" \
                    % uuid)
            return False

        if meta['state'].lower() == "signed":
            log.info("Puppet API: Cert for %s is already signed" % uuid)
            return True

        r, c = self.http.put("/root/certificate_status/%s-%s" \
                % (fqdn, uuid), 
                headers = {'Accept': 'pson',
                           'Content-Type': 'text/pson'},
                body = json.dumps({"desired_state":"signed"}))

        # We shouldn't get a 404 here, we just poked it
        if r.status != 200:
            log.error("Puppet API: Error signing cert for %s: %s - %s" \
                    % (uuid, r.reason, c))
            return False

        # Request should now be signed
        return True
    
