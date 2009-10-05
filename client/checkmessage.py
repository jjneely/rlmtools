import sys
import base64

sys.path.append("/usr/share/rlmtools")

from message import Message

msg = Message()
msg.load(sys.argv[1])

print "Message Type: %s" % msg.data['type']
print "Message Success: %s" % msg.data['success']
print "Message Timestamp: %s" % msg.data['timestamp']

blob = base64.decodestring(msg.data['data'])

print "=============== Message ==============="
print blob

