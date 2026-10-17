#!/usr/bin/env python3
# Stage the ~11GB dense core from sshfs -> local sparse files (short-read tolerant).
import json, os, struct, glob
SRC='/home/stevo/glm-remote'; DST='/home/stevo/glm-local'
os.makedirs(DST, exist_ok=True)
a=json.load(open(f'{SRC}/.coli_analysis.json'))['analysis']
dense=set(t['name'] for t in a['dense_tensors'])

def read_range(f, start, length):
    f.seek(start); out=bytearray(); rem=length
    while rem>0:
        c=f.read(min(8*1024*1024, rem))
        if not c: raise IOError(f'EOF at {start}+{length-rem}')
        out+=c; rem-=len(c)
    return out

for nm in ['config.json','generation_config.json','tokenizer_config.json',
           'tokenizer.json','.coli_analysis.json','.coli_usage']:
    sp=f'{SRC}/{nm}'
    if os.path.exists(sp):
        with open(sp,'rb') as s, open(f'{DST}/{nm}','wb') as d: d.write(s.read())

files=sorted(glob.glob(f'{SRC}/out-*.safetensors'))
tot=0
for i,fp in enumerate(files):
    bn=os.path.basename(fp); sz=os.path.getsize(fp)
    with open(fp,'rb') as f:
        hl=struct.unpack('<Q', f.read(8))[0]
        hdr_b=f.read(hl); hdr=json.loads(hdr_b); base=8+hl
        with open(f'{DST}/{bn}','wb') as o:
            o.write(struct.pack('<Q',hl)); o.write(hdr_b); o.truncate(sz)
            for name,meta in hdr.items():
                if name=='__metadata__' or name not in dense: continue
                o0,o1=meta['data_offsets']; L=o1-o0
                data=read_range(f, base+o0, L)
                o.seek(base+o0); o.write(data); tot+=L
    print(f'[{i+1}/{len(files)}] {bn} {tot/1e9:.2f}GB', flush=True)
print(f'DONE dense={tot/1e9:.2f}GB', flush=True)
