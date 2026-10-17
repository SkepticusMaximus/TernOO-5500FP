#!/usr/bin/env python3
# Runs on LENNY. Reads /mnt/glm locally, streams aux files + dense-tensor bytes to stdout.
import json, os, struct, glob, sys
SRC='/mnt/glm'
a=json.load(open(f'{SRC}/.coli_analysis.json'))['analysis']
dense=set(t['name'] for t in a['dense_tensors'])
out=sys.stdout.buffer
aux=['config.json','generation_config.json','tokenizer_config.json',
     'tokenizer.json','.coli_analysis.json','.coli_usage']
for nm in aux:
    p=f'{SRC}/{nm}'
    if not os.path.exists(p): continue
    d=open(p,'rb').read(); nb=nm.encode()
    out.write(b'\x00'+struct.pack('<H',len(nb))+nb+struct.pack('<Q',len(d))+d)
for fp in sorted(glob.glob(f'{SRC}/out-*.safetensors')):
    bn=os.path.basename(fp); sz=os.path.getsize(fp)
    with open(fp,'rb') as f:
        hl=struct.unpack('<Q',f.read(8))[0]; hb=f.read(hl); hdr=json.loads(hb); base=8+hl
        ranges=sorted((base+m['data_offsets'][0], m['data_offsets'][1]-m['data_offsets'][0])
                      for n,m in hdr.items() if n!='__metadata__' and n in dense)
        nb=bn.encode()
        out.write(b'\x01'+struct.pack('<H',len(nb))+nb+struct.pack('<Q',sz)+struct.pack('<Q',hl)+hb+struct.pack('<I',len(ranges)))
        for off,ln in ranges:
            out.write(struct.pack('<QQ',off,ln)); f.seek(off); rem=ln
            while rem>0:
                c=f.read(min(8<<20,rem)); out.write(c); rem-=len(c)
out.write(b'\xff'); out.flush()
