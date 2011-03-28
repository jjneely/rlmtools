import sys
import logging
import traceback
import Bcfg2.Server.Plugin

from Bcfg2.Server.Plugins.Metadata import Metadata, MetadataQuery, \
        MetadataConsistencyError, MetadataRuntimeError

from rlmtools.server import Server
from rlmtools.rlattributes import RLAttributes

# To setup new hosts...
from rlmtools.apiServer import APIServer
import rlmtools.uuid

# To setup RLMTools configuration
import rlmtools.configDragon
from rlmtools.constants import defaultConfFiles

if rlmtools.configDragon.config is None:
    # XXX: How do we customize configfiles here?
    rlmtools.configDragon.initConfig(defaultConfFiles)

# We get our client metadata information from a database not the local
# clients.xml files in the Bcfg2 repository.

logger = logging.getLogger('Bcfg2.Plugins.RLMetadata')


class ImmutableDict(dict):

    def __setitem__(self, key, value): raise TypeError

    def __delitem__(self, key): raise TypeError

    def update(self, d): raise TypeError

class Clients(ImmutableDict):

    def __init__(self):
        dict.__init__(self)
        self._rattrs = RLAttributes()
        self._rlm = self._rattrs._admin

    def __delitem__(self, key):
        logger.warning("Tried to delete client: %s" % key)
        logger.warning("WTF is going on?")

    def __setitem__(self, key, value):
        id = self._rlm.getHostID(key)
        if id is None:
            raise KeyError
        self._rattrs.setHostAttribute(id, 'bcfg2.profile', str(value))
        # setHostAttribute runs its own commit as a write transaction

    def __getitem__(self, key):
        id = self._rlm.getHostID(key)
        self._rlm.conn.commit()
        if id is None:
            raise KeyError
        value = self._rattrs.getHostAttr(id, 'bcfg2.profile')
        if value is None:
            return 'default'
        else:
            return value

    def __contains__(self, key):
        id = self._rlm.getHostID(key)
        self._rlm.conn.commit()
        return id is not None

    def keys(self):
        keys = self._rlm.getAllHosts().keys()
        self._rlm.conn.commit()
        return keys

    def iteritems(self):
        for key in self.keys():
            yield (key, self[key])

class Floating(object):

    def __init__(self):
        self._rattrs = RLAttributes()
        self._rlm = self._rattrs._admin

    def __contains__(self, key):
        id = self._rlm.getHostID(key)
        self._rlm.conn.commit()
        return id is not None

class UUID(ImmutableDict):
    # XXX: Hostnames must be returned in lower case for compare operations

    # XXX: This calls commit() even though we only read from the DB
    # we read a lot, rarely commit, and end up causing transactional
    # issues even with MyIASM

    def __init__(self):
        self._rattrs = RLAttributes()
        self._rlm = self._rattrs._admin

    def __contains__(self, key):
        # XXX: This needs to be a case insensitive compare on the hostname
        # MySQL isn't case senitive to begin with so that's how we are
        # working here.  But it may bite us in the future.
        host = self._rlm.getHostByUUID(key)
        self._rlm.conn.commit()
        return host is not None

    def __getitem__(self, key):
        host = self._rlm.getHostByUUID(key)
        self._rlm.conn.commit()
        if host is None:
            raise KeyError
        else:
            return host.lower()

    def keys(self):
        keys = self._rlm.getAllUUIDs()
        self._rlm.conn.commit()
        return keys

    def iteritems(self):
        for k in self.keys():
            yield (k, self[k].lower())

class RLMetadata(Metadata):

    def __init__(self, core, datastore, watch_clients=True):
        logger.info("Bringing up RLMetadata...")
        Bcfg2.Server.Plugin.Plugin.__init__(self, core, datastore)
        Bcfg2.Server.Plugin.Metadata.__init__(self)
        Bcfg2.Server.Plugin.Statistics.__init__(self)
        if watch_clients:
            try:
                core.fam.AddMonitor("%s/%s" % (self.data, "groups.xml"), self)
                # We no longer watch clients.xml -- RLMetadata gets data from DB
            except:
                raise Bcfg2.Server.Plugin.PluginInitError
        self.states = {}
        if watch_clients:
            self.states = {"groups.xml":False}
        self.addresses = {}
        self.raddresses = {}
        self.auth = {}
        self.clients = Clients()
        self.aliases = {}
        self.raliases = {}
        self.groups = {}
        self.cgroups = {}
        self.public = []
        self.profiles = []
        self.categories = {}
        self.bad_clients = {}
        self.uuid = UUID()
        self.secure = []
        self.floating = Floating()
        self.passwords = {}
        self.session_cache = {}
        self.clientdata = None
        self.clientdata_original = None
        self.default = None
        self.pdirty = False
        self.extra = {'groups.xml':[]}
        self.password = core.password
        self.query = MetadataQuery(core.build_metadata,
                                   lambda:self.clients.keys(),
                                   self.get_client_names_by_groups,
                                   self.get_client_names_by_profiles,
                                   self.get_all_group_names)

    #def HandleEvent(self, event):
    #    # Ignore any of the FAM events for clients.xml
    #    filename = event.filename.split('/')[-1]
    #    if filename == "clients.xml":
    #        return
    #    else:
    #        return Metadata.HandleEvent(self, event)

    def write_back_clients(self):
        # For saftey...if this function is called something needs to be fixed
        logger.error("RLMetadata.write_back_clients() called...badness")

    def set_profile(self, client, profile, addresspair):
        logger.info("RLMetadata: Asserting client %s to profile %s" % \
                (client, profile))

        if False in self.states.values():
            raise MetadataRuntimeError
        if profile not in self.public:
            logger.error("Failed to set client %s to private group %s" % \
                    (client, profile))
            raise MetadataConsistencyError
        if client in self.clients:
            logger.info("Changing %s group from %s to %s" % \
                    (client, self.clients[client], profile))
            self.clients[client] = profile
        else:
            logger.info("Creating new client: %s, profile %s" % \
                         (client, profile))
            self.add_client(client, {'profile':profile})


    def add_client(self, client_name, attribs):
        logger.error("RLMetadata: Inside add_client()" \
                     "WE SHOULD NOT BE HERE.  ABORTING!")
        assert(False)

        # The following left for future notes.  It is not executed
        logger.info("RLMetadata: Creating new host %s with attributes %s" % \
                    (client_name, attribs))

        # XXX: The client normally provides a UUID rather than RLMTools
        # generating one for it.  In this specific case (new Bcfg2 host)
        # we are left with no choice but to assume its UUID.  Somehow
        # this needs to be made consistant.

        u = str(rlmtools.uuid.uuid4())
        logger.warning("RLMetadata: Making up UUID %s for %s" \
                       % (u, client_name))

        # APIv2 specified here
        server = APIServer(2, client_name, u)
        attributes = RLAttributes()

        # Setup a new client.  We've not seen this client before
        # it becomes un-supported
        host_id, sid = server.initHost(client_name, 0)

        for key, value in attribs.iteritems():
            attributes.setHostAttribute(host_id, "bcfg2.%s" % key, value)

    def update_client(self, client_name, attribs):
        logger.info("RLMetadata: Updating client %s with %s" % \
                    (client_name, attribs))

        attributes = RLAttributes()
        host_id = attributes.getHostID(client_name)
        for key, value in attribs.iteritems():
            attributes.setHostAttribute(host_id, "bcfg2.%s" % key, value)

    def AuthenticateConnection(self, cert, user, password, address):
        "Enforce client's authenticating with their UUID."
        
        try:
            # Make sure we exist
            if user not in self.uuid:
                # We don't?  Or bad UUID?  Deny the client.
                s = "RLMetadata: Denying UUID '%s' with address '%s'. " \
                        "Unknown UUID/client."
                logger.info(s % (user, address))
                return False

            return Metadata.AuthenticateConnection(self, cert, user, 
                                                   password, address)
        except Exception, e:
            text = traceback.format_exception(sys.exc_type,
                                              sys.exc_value,
                                              sys.exc_traceback)
            logger.critical("Exception occured authenticating client: %s" \
                           % user)
            for line in text:
                logger.critical(line)
        
        return False


def main():
    uuids = UUID()
    for uuid, host in uuids.iteritems():
        if uuid in uuids:
            print "%s is %s and is in our UUID dictionary" % (uuid, host)
        else:
            print "%s is %s and is NOT in our UUID dictionary" % (uuid, host)

    clients = Clients()
    floating = Floating()
    clients['linux00tst.unity.ncsu.edu'] = 'jack-fc14-x86_128'
    for key, value in clients.iteritems():
        print "clients['%s'] = %s" % (key, value)
        if key in floating:
            print "%s is floating" % key

if __name__ == "__main__":
    main()

