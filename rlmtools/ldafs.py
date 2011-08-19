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

def equalACLs(ld, afs):
    # Return true if the list of afs (pts, perms) tuples matches
    # the given list of ld (name, pts, perms) tuples.  Ment to work
    # with the above two functions

    # acceptWrite set to True will mean that an LD Admin perm will
    # match an AFS admin OR write permission.

    if len(afs) != len(ld): return False

    for acl in ld:
        if acl[2] == 'admin':
            if not( (acl[1], 'admin') in afs or (acl[1], 'write') in afs):
                return False
        else:
            if (acl[1], acl[2]) not in afs: return False

    return True

def LDtoAFS(acl):
    # Translate LD ACL to its equivallent AFS PTS permission
    if acl[1] == 'linux':
        # The linux ACL always has admin even in AFS
        return ('linux', 'admin')
    return (acl[1], acl[2])

def AFSpermLD(perm):
    # Translate AFS PTS permission to LD ACL equivallent
    if perm == 'admin':
        ret = 'admin'
    elif perm == 'write':
        ret = 'admin'
    elif perm == 'read':
        ret = 'read'
    else:
        ret = 'unknown'
        
    return ret

def LDpermAFS(perm):
    # Translate LD permission to AFS PTS equivallent
    if perm == 'admin':
        ret = 'write'
    elif perm == 'write':
        ret = 'write'
    elif perm == 'read':
        ret = 'read'
    else:
        ret = 'unknown'
        
    return ret

def equalPerm(ld, afs):
    # Compare this LD permission (like read, write, admin) to the AFS perm
    # Return True if equal, False otherwise
    # ld is part of the result from LDtoAFS()
    if afs not in rLDBitMap.keys():
        return False
    return ld == AFSpermLD(afs)

