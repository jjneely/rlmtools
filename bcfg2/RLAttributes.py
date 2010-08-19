#!/usr/bin/python

import sys
import traceback
import logging
import Bcfg2.Server.Plugin

import rlmtools.configDragon
from rlmtools.constants import defaultConfFiles
from rlmtools.rlattributes import RLAttributes as RLA

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

    def get_additional_data(self, metadata):
        if metadata.uuid is None or metadata.uuid == "":
            # Host doesn't have a UUID, probably not registered
            # with RLMTools yet at the least
            return {}

        logger.info("Building attributes for UUID %s" % metadata.uuid)
        try:
            host_id = self.rla.getUUIDID(metadata.uuid)
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
        return []
