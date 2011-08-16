# ldafs.py -- Common AFS methods for the RLMTools Server

import afs.acl
import afs.fs

AFSBitMap = {
    0x7f: 'admin',
    0x3f: 'write',
    0x9 : 'read',
    0x8 : 'look',
        }

# To Match against AFS.  So admin implies write/read and write implies read
LDBitMap = {
    0x0: 'unknown',
    0x1: 'admin',
    0x2: 'write',
    0x3: 'admin',
    0x4: 'read',
    0x5: 'admin',
    0x6: 'write',
    0x7: 'admin',
        }

rLDBitMap = {
    'admin': 0x7,
    'write': 0x6,
    'read' : 0x1,
    }

def fsla(path):
    # fs la <path>
    if not afs.fs.inafs(path):
        return None

    ret = []
    acls = afs.acl.ACL.retrieve(path)
    # Ignore negative ACLs for now
    for i in acls.pos.keys():
        # We filter out some PTS groups we are not interested in managing.
        if i.startswith('admin:'): continue
        if i in ['system:administrators']: continue

        # Next we map AFS permissions to something similar to LD's
        # bitfield based permissions.  We have admin, write, read, look,
        # and other
        if acls.pos[i] in AFSBitMap:
            perm = AFSBitMap[acls.pos[i]]
        else:
            perm = 'other'

        ret.append((i, perm))

    return ret

def matchACLToAFS(ldacls, restrictive=False):
    # This takes the output of _misc.getDeptACLs(i['dept_id']) and
    # transmutes that to something that can be matched against the 
    # permissions returned by fsla()

    # restrictive -- Remove any LD ACLs with only read access
    ret = []
    for acl in ldacls:
        if restrictive and acl['perms'] == 4: continue
        ret.append((acl['name'], acl['pts'], LDBitMap[acl['perms']]))

    return ret

def equalACLs(afs, ld, acceptWrite=False):
    # Return true if the list of afs (pts, perms) tuples matches
    # the given list of ld (name, pts, perms) tuples.  Ment to work
    # with the above two functions

    # acceptWrite set to True will mean that an LD Admin perm will
    # match an AFS admin OR write permission.

    if len(afs) != len(ld): return False

    for acl in ld:
        if acceptWrite and acl[2] == 'admin':
            if not( (acl[1], 'admin') in afs or (acl[1], 'write') in afs):
                return False
        else:
            if (acl[1], acl[2]) not in afs: return False

    return True

def LDtoAFS(acl):
    # Translate LD ACL to its equivallent AFS PTS permission
    if acl[2] == 'admin':
        return (acl[1], 'write')
    if acl[2] == 'write':
        return (acl[1], acl[2])
    if acl[2] == 'read':
        return (acl[1], acl[2])
    return None

def AFStoLD(acl):
    # Translate AFS PTS permission to LD ACL equivallent
    if acl[1] == 'admin':
        return (acl[0], acl[0], 'admin')
    if acl[1] == 'write':
        return (acl[0], acl[0], 'admin')
    if acl[1] == 'read':
        return (acl[0], acl[0], 'read')
    return None

def LDinLDs(ld, lds):
    # Is the LD ACL 'ld' in the list of LD ACLs 'lds'?
    for i in lds:
        if (ld[1], ld[2]) == (i[1], i[2]): return True
    return False

