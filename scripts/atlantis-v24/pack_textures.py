"""Convert authored PNG surfaces to lossless WebP; retain source dimensions/pixels and all artwork JPEG bytes."""
import json,struct,io,hashlib
from pathlib import Path
from PIL import Image,ImageChops
OUT=Path('/Users/eee/Desktop/works/atlantis-v24/output');p=OUT/'atlantis-web.glb';raw=p.read_bytes();parts={};i=12
while i<len(raw):
 n,t=struct.unpack_from('<II',raw,i);i+=8;parts[t]=raw[i:i+n];i+=n
j=json.loads(parts[0x4e4f534a]);binary=parts[0x004e4942];replacements={};changes=[]
for idx,im in enumerate(j['images']):
 if not im.get('name','').startswith('V24_'):continue
 v=j['bufferViews'][im['bufferView']];source=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
 pic=Image.open(io.BytesIO(source)).convert('RGB');dst=io.BytesIO();pic.save(dst,format='WEBP',lossless=True,method=6);encoded=dst.getvalue();decoded=Image.open(io.BytesIO(encoded)).convert('RGB');assert ImageChops.difference(pic,decoded).getbbox() is None
 replacements[im['bufferView']]=encoded;im['mimeType']='image/webp'
 for tex in j['textures']:
  if tex.get('source')==idx:del tex['source'];tex.setdefault('extensions',{})['EXT_texture_webp']={'source':idx}
 changes.append({'name':im['name'],'source_bytes':len(source),'web_bytes':len(encoded),'size':pic.size,'decoded_RGB_identical':True})
# Repack every buffer view, including Meshopt payload offsets that live outside ordinary buffer views.
# Meshopt extensions point to byte ranges in the original buffer; keep those ranges valid by appending new images.
# Then remove obsolete PNG payload by rebuilding a unified range table and remapping all references.
ranges={}
for v in j['bufferViews']:
 if v.get('buffer',0)==0:ranges[(v.get('byteOffset',0),v['byteLength'])]=replacements.get(j['bufferViews'].index(v),binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])
 ext=v.get('extensions',{}).get('EXT_meshopt_compression')
 if ext and ext['buffer']==0:ranges[(ext.get('byteOffset',0),ext['byteLength'])]=binary[ext.get('byteOffset',0):ext.get('byteOffset',0)+ext['byteLength']]
packed=bytearray();offsets={}
for key,content in sorted(ranges.items()):
 while len(packed)%4:packed.append(0)
 offsets[key]=(len(packed),len(content));packed.extend(content)
for v in j['bufferViews']:
 if v.get('buffer',0)==0:v['byteOffset'],v['byteLength']=offsets[(v.get('byteOffset',0),v['byteLength'])]
 ext=v.get('extensions',{}).get('EXT_meshopt_compression')
 if ext and ext['buffer']==0:ext['byteOffset'],ext['byteLength']=offsets[(ext.get('byteOffset',0),ext['byteLength'])]
while len(packed)%4:packed.append(0)
j['buffers'][0]['byteLength']=len(packed)
for k in ['extensionsUsed','extensionsRequired']:
 j.setdefault(k,[])
 if 'EXT_texture_webp' not in j[k]:j[k].append('EXT_texture_webp')
js=json.dumps(j,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
result=struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(packed))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(packed),0x004e4942)+packed
p.write_bytes(result);report={'method':'lossless WebP for new PBR surfaces; identical browser-decoded RGB pixels; original artwork JPEG bytes untouched','before':len(raw),'after':len(result),'textures':changes};(OUT/'texture-pack-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
