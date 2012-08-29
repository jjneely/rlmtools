#!/usr/bin/python

import re
import sys
import yaml
import optparse
import logging
import logging.handlers

from rlmtools import rlattributes
from rlmtools import apiServer
from rlmtools import configDragon
from rlmtools.constants import defaultConfFiles

# This matches our "fqdn-UUID" cert naming scheme
regex = "([-_a-zA-Z0-9.]+)-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"

# Some additional magic to parse the Puppet/Ruby YAML objects
def construct_ruby_object(loader, suffix, node):
    return loader.construct_yaml_map(node)

def construct_ruby_sym(loader, node):
    return loader.construct_yaml_str(node)

yaml.add_multi_constructor(u"!ruby/object:", construct_ruby_object)
yaml.add_constructor(u"!ruby/sym", construct_ruby_sym)

def getFacts(clientcert):
    fd = open("/var/lib/puppet/yaml/facts/%s.yaml" % clientcert)
    map = yaml.load(fd.read())
    fd.close()
    return map["values"]

def getParams(hostname, uuid):
    RLA = rlattributes.RLAttributes()
    api = apiServer.APIServer(2, hostname, uuid)
    host_id = api.getUuidID(uuid)
    if host_id is None:
        # Unregistered host
        return {}

    m, a = RLA.hostAttrs(host_id)
    a["meta"] = m
    a["support"] = api.isSupported()
    dept = api.getDeptName(api.getHostDept(host_id))

    # dept is a top-level, we use this to match the puppet environment
    # Also, dept in the database is already normalized
    return { "rlmtools": a,
             "rlmdept" : dept,
           }

def main():
    parser = optparse.OptionParser()
    parser.add_option("-C", "--configfile", action="store",
            default=defaultConfFiles,
            dest="configfile",
            help="Configuration file")
    (options, args) = parser.parse_args()

    # Start up configuration/logging/databases of RLMTools
    configDragon.initConfig(options.configfile)
    log = logging.getLogger("xmlrpc.enc")

    argc = len(args)

    if argc < 1:
        log.error("ENC called without host/certname as first argument")
        sys.exit(1)

    certname = args[0]
    match = re.match(regex, certname)
    if match is not None:
        hostname = match.group(1)
        uuid = match.group(2)
        log.info("Generating YAML for puppet with RLMTools attributes for "
                 "host %s and UUID: %s" % (hostname, uuid))
        doc = {"parameters": getParams(hostname, uuid), }
        print yaml.dump(doc)
    else:
        log.error("Could not parse certname into host and UUID pair.")
        # A non-realm-linux box?  Sure, we'll take these...might as well
        print yaml.dump(
            {
                "parameters": 
                {
                    "rlmdept": "UNKNOWN",
                }
            } )

#    log.info("%s has environment %s" % (hostname, 
#        getFacts(certname)["environment"]))



if __name__ == "__main__":
    main()

