#!/usr/bin/env python3
# Runs on HUEY. Reads the stream from Lenny, writes proper sparse files.
import sys, os, struct
DST='/home/stevo/glm-local'; os.makedirs(DST, exist_ok=True)
inp=sys.stdin.buffer
def rd(n):
    b=bytearray()
    while len(b)<n:
        c=inp.read(n-len(b))
        if not c: raise EOFError('stream truncated')
        b+=c
    return bytes(b)
n=0
with open('/home/stevo/stream.log','w') as log:
    while True:
        t=inp.read(1)
        if not t or t==b'\xff': break
        if t==b'\x00':
            nl=struct.unpack('<H',rd(2))[0]; nm=rd(nl).decode()
            dl=struct.unpack('<Q',rd(8))[0]; open(f'{DST}/{nm}','wb').write(rd(dl))
        elif t==b'\x01':
            nl=struct.unpack('<H',rd(2))[0]; bn=rd(nl).decode()
            sz=struct.unpack('<Q',rd(8))[0]; hl=struct.unpack('<Q',rd(8))[0]; hb=rd(hl)
            nr=struct.unpack('<I',rd(4))[0]
            with open(f'{DST}/{bn}','wb') as o:
                o.write(struct.pack('<Q',hl)); o.write(hb); o.truncate(sz)
                for _ in range(nr):
                    off,ln=struct.unpack('<QQ',rd(16)); o.seek(off); o.write(rd(ln))
            n+=1; log.write(f'{n}\n'); log.flush()
    log.write('DONE\n'); log.flush()
