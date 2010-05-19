import sys
import base64

sys.path.append("/usr/share/rlmtools")

from message import Message

if len(sys.argv) != 2:
    print "Usage: %s <message file>" % sys.argv[0]
    sys.exit(1)

msg = Message()
msg.load(sys.argv[1])

print "Message Type: %s" % msg.data['type']
print "Message Success: %s" % msg.data['success']
print "Message Timestamp: %s" % msg.data['timestamp']

blob = base64.decodestring(msg.data['data'])

print "=============== Message ==============="
print blob

