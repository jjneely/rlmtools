import sys
import xmlrpclib
import os

sys.path.append("/afs/eos/project/realmlinux/py-modules")
import ezPyCrypto

publicKey = "/etc/sysconfig/RLKeys/rkhost.pub"
privateKey = "/etc/sysconfig/RLKeys/rkhost.priv"
publicRLKey = "/etc/sysconfig/RLKeys/realmlinux.pub"

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

server = xmlrpclib.ServerProxy("https://secure.linux.ncsu.edu/xmlrpc/handler.py")

keypair = getLocalKey()
if keypair == None:
    print "Unsupported workstation.  Using default key."
    rhnkey = "6ed40e5c831bd8a8d706f0abe8f44f09"
else:
    pubKey = keypair.exportKey()
    sig = keypair.signString(pubKey)
    rhnkey = server.getActivationKey(pubKey, sig)

print rhnkey

