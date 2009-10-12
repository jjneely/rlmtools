import pprint
from rlmtools.adminServer import AdminServer

from webKickstart.libwebks import LibWebKickstart
p = pprint.PrettyPrinter()

admin = AdminServer()
webks = LibWebKickstart()
host = 'linux10tst.unity.ncsu.edu'
attributes = {'foo':'test test test',
              'bar':'luggage'}

p.pprint(webks.getEverything(host))

######################

host_id = admin.getHostID(host)
print "Host ID for %s is %s" % (host, host_id)

dept_id = admin.getDeptID('oit')
print "Dept ID for %s is %s" % ('oit', dept_id)

host_ptr = admin.getHostAttrPtr(host_id)
dept_ptr = admin.getDeptAttrPtr(dept_id)
print "Host attribute pointer: %s" % host_ptr
print "Dept attribute pointer: %s" % dept_ptr

##################################

for ptr in [host_ptr, dept_ptr]:
    for a in attributes.keys():
        print
        t = admin.getAttributes(ptr, a)
        print "Current attributes for ptr %s, key %s: %s" % (ptr, a, t)
        print "Adding: %s:%s" % (a, attributes[a])
        admin.setAttribute(ptr, a, 666, attributes[a])
        t = admin.getAttributes(ptr, a)
        print "Current attributes for ptr %s, key %s: %s" % (ptr, a, t)
        print "Keys for ptr %s: %s" % (ptr, admin.getAttrKeys(ptr))
        print "Removing attribute key %s from ptr %s" % (a, ptr)
        admin.removeAttribute(ptr, t[0]['attr_id'])

# Okay, now create a dept attribute and leave it there
dept_id = admin.getDeptID('itd-cls')
dept_ptr = admin.getDeptAttrPtr(dept_id)
t = admin.getAttributes(dept_ptr, 'testKey')
if len(t) == 0:
    admin.setAttribute(dept_ptr, 'testKey', 1, "test value")

dept_id = admin.getDeptID('itd')
dept_ptr = admin.getDeptAttrPtr(dept_id)
t = admin.getAttributes(dept_ptr, 'testITD')
if len(t) == 0:
    admin.setAttribute(dept_ptr, 'testITD', 1, "Oh YEAH!")

