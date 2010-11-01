#!/usr/bin/python

import sys
import re
import os
import traceback
import logging
import Bcfg2.Server.Plugin

import rlmtools.configDragon
from rlmtools.constants import defaultConfFiles
from rlmtools.rlattributes import RLAttributes as RLA
from rlmtools.server import Server as RLServer

if rlmtools.configDragon.config is None:
    # XXX: How do we customize configfiles here?
    rlmtools.configDragon.initConfig(defaultConfFiles)

logger = logging.getLogger('Bcfg2.Plugins.RLAttributes')

class RLAttributes(Bcfg2.Server.Plugin.Plugin,
                   Bcfg2.Server.Plugin.Connector):

    name = 'RLAttributes'
    version = '0'

    def __init__(self, core, datastore):
        logger.info("Bringing up RLAttributes...")
        Bcfg2.Server.Plugin.Plugin.__init__(self, core, datastore)
        Bcfg2.Server.Plugin.Connector.__init__(self)
        self.rla = RLA()
        self.rlserver = RLServer()
        self.webksConf = "%s/webkickstart/groups.conf" % datastore

    def get_additional_data(self, metadata):
        if metadata.uuid is None or metadata.uuid == "":
            # Host doesn't have a UUID, probably not registered
            # with RLMTools yet at the least
            return {}

        logger.info("Building attributes for UUID %s" % metadata.uuid)
        try:
            host_id = self.rlserver.getUuidID(metadata.uuid)
            if host_id is None:
                logger.warning("Could not find a host_id for UUID %s" \
                               % metadata.uuid)
                return {}
            meta, attributes = self.rla.hostAttrs(host_id)
            attributes.update(meta)
            return attributes
        except Exception, e:
            text = traceback.format_exception(sys.exc_type,
                                              sys.exc_value,
                                              sys.exc_traceback)

            logger.warning("RLAttributes: An exception occured!")
            logger.warning("Exception: %s" % text)

        return {}

    def get_additional_groups(self, metadata):
        if metadata.uuid is None or metadata.uuid == "":
            return []

        logger.info("Building groups for UUID %s" % metadata.uuid)
        groups = []
        
        try:
            host_id = self.rlserver.getUuidID(metadata.uuid)
            if host_id is None:
                logger.warning("Could not find a host_id for UUID %s" \
                               % metadata.uuid)
                return groups
            support = self.rlserver.isSupported(host_id)
            meta, attributes = self.rla.hostAttrs(host_id)
            attributes.update(meta)
        except Exception, e:
            text = traceback.format_exception(sys.exc_type,
                                              sys.exc_value,
                                              sys.exc_traceback)

            logger.warning("RLAttributes: An exception occured!")
            logger.warning("Exception: %s" % text)

        if 'bcfg2.groups' in attributes:
            groups.extend(attributes['bcfg2.groups'].split())
        if support is not True and 'feature-nosupport' not in groups:
            groups.append('feature-nosupport')

        if not os.access(self.webksConf, os.R_OK):
            return groups

        # Now look for speacial keys
        logger.warning("Reading %s" % self.webksConf)
        patt = re.compile('^\s*([-._a-zA-Z0-9]+)\s*:\s*([-._a-zA-Z0-9]+)\s*$')
        for line in open(self.webksConf).readlines():
            m = patt.match(line.strip())
            if m is not None:
                key = m.group(1)
                grp = m.group(2)
                logger.warning("Found %s:%s" % (key, grp))
                if key in attributes and attributes[key] is not None:
                    if grp not in groups:
                        groups.append(grp)

        return groups
