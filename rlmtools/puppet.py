import re
import os
import os.path
import logging
import json
import lzma

from socket import gethostname
from datetime import datetime
from dateutil import tz

import restclient

log = logging.getLogger("xmlrpc")

facts_path = "/afs/bp/adm/puppet/var/yaml/facts/"
reports_path = "/afs/bp/adm/puppet/var/reports"

def findPuppetInventory(uuid):
    """Returns None or a YAML string of the latest Puppet facts for this
       host matching the given UUID."""
    if uuid is None:
        # We check clients that have not completely registered where uuid 
        # is None.
        return None

    p = facts_path
    facts = None
    uuid = uuid.lower()
    try:
        ls = os.listdir(p)
    except OSError, e:
        log.warning("In findPuppetInventory(): %s" % str(e))
        return None

    for i in ls:
        if uuid in i.lower():
            # UUID is a substring of the file name
            facts = os.path.join(p, i)
            break

    if facts is None:
        return None

    fd = open(facts)
    blob = fd.read()
    fd.close()
    if facts.endswith(".xz"):
        return lzma.decompress(blob)
    else:
        return blob

def findPuppetReports(uuid):
    """Return None or a list of files, each being time stamped and each
       being a LZMA compressed or plain text YAML file of a Puppet run
       report."""
    if uuid is None: return None
    uuid = uuid.lower()
    d = None
    try:
        ls = os.listdir(reports_path)
    except OSError, e:
        log.warning("In findPuppetReports(): %s" % str(e))
        return None

    for i in ls:
        if uuid in i.lower():
            # UUID is a substring of this directory name
            d = os.path.join(reports_path, i)
            break

    if d is None:
        return None
    ret = os.listdir(d)
    return [ os.path.join(d, i) for i in ret ]

def readPuppetReport(filename):
    """Return a string from the YAML report file given."""
    if not os.path.exists(filename):
        return None

    fd = open(filename)
    blob = fd.read()
    fd.close()

    if filename.endswith(".xz"):
        return lzma.decompress(blob)

    return blob

def getTimestamp(filename):
    """Return a datetime object representing the given report's
       timestamp.  Its regex'd out of the file name and will return
       None if it fails."""

    r = ".*([0-9]{4})([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{2})\.yaml(?:\.zx)?"
    m = re.match(r, filename)
    if m is not None:
        d = datetime(
                     year=int(m.group(1)),
                     month=int(m.group(2)),
                     day=int(m.group(3)),
                     hour=int(m.group(4)),
                     minute=int(m.group(5)),
                     tzinfo=tz.tzutc(),
                    )
        return d
    return None

def localPuppetDate(d):
    """Return a timestamp string in local time from the Puppet report
       timestamp d."""

    return d.astimezone(tz.tzlocal()).isoformat(" ")

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
        client = "%s-%s" % (fqdn.lower(), uuid)
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
    
