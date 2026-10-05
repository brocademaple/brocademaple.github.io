"""V2.4 model, artwork, material and compression contract."""
import json,struct,hashlib,io
from pathlib import Path
from PIL import Image,ImageChops
OUT=Path('/Users/eee/Desktop/works/atlantis-v24/output');REPO=Path('/Users/eee/Desktop/code/selfy/brocade-portfolio')
def read(name):
 data=(OUT/name).read_bytes();assert data[:4]==b'glTF';parts={};i=12
 while i<len(data):n,t=struct.unpack_from('<II',data,i);i+=8;parts[t]=data[i:i+n];i+=n
 return json.loads(parts[0x4e4f534a]),parts[0x004e4942]
def images(j,b):
 return {im['name']:b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']] for im in j['images'] for v in [j['bufferViews'][im['bufferView']]]}
def tri(j):return sum(j['accessors'][p['indices']]['count']//3 for m in j['meshes'] for p in m['primitives'])
a,ab=read('atlantis-gallery-master-v2-polish.glb');w,wb=read('atlantis-web.glb');ai=images(a,ab);wi=images(w,wb)
assert tri(a)==tri(w);assert set(ai)==set(wi)
for name in ai:
 if name.startswith('V24_'):
  p=Image.open(io.BytesIO(ai[name])).convert('RGB');q=Image.open(io.BytesIO(wi[name])).convert('RGB');assert p.size==q.size and ImageChops.difference(p,q).getbbox() is None,name
 else:assert ai[name]==wi[name],name
catalog=json.loads((OUT/'artworks.json').read_text());bythumb={a['thumb']:a for a in catalog};works=[]
for n in a['nodes']:
 e=n.get('extras',{})
 if not e.get('gallery_interactive'):continue
 thumb=e['gallery_artwork_thumb'];assert thumb in bythumb;works.append(thumb);p=a['meshes'][n['mesh']]['primitives'][0];m=a['materials'][p['material']];texture=a['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']];im=a['images'][texture['source']];assert ai[im['name']]==(REPO/'static'/thumb.lstrip('/')).read_bytes();assert 'TEXCOORD_0' in p['attributes']
 acc=a['accessors'][p['attributes']['POSITION']];bv=a['bufferViews'][acc['bufferView']];start=bv.get('byteOffset',0)+acc.get('byteOffset',0);stride=bv.get('byteStride',12);vs=[struct.unpack_from('<3f',ab,start+i*stride) for i in range(acc['count'])];height=max(v[1] for v in vs)-min(v[1] for v in vs);width=max(((u[0]-v[0])**2+(u[2]-v[2])**2)**.5 for u in vs for v in vs);assert abs(width/height-bythumb[thumb]['aspect'])<.003
assert len(works)==len(set(works))==42
mats=[m for m in a['materials'] if m['name'].startswith('V24_')]
for m in mats:
 pbr=m['pbrMetallicRoughness'];assert 'baseColorTexture' in pbr and 'metallicRoughnessTexture' in pbr and 'normalTexture' in m and 'occlusionTexture' in m,m['name']
assert len(mats)==4
nav=json.loads((OUT/'navigation.json').read_text());markers={n['extras']['gallery_nav_id']:n['translation'] for n in a['nodes'] if 'gallery_nav_id' in n.get('extras',{})}
assert len(markers)==8
for key,p in markers.items():assert all(abs(x-y)<1e-4 for x,y in zip(p,nav['spawns'][key]['position'])),key
result={'passed':True,'triangles':tri(w),'same_geometry_in_both_modes':True,'artworks_original_JPEG_bytes':len(works),'source_aspect_preserved':True,'new_PBR_materials':[m['name'] for m in mats],'new_texture_decoded_pixels_preserved':True,'navigation_markers_match_master':True,'floor_triangles':len(nav['floors']),'obstacle_triangles':len(nav['obstacles']),'web_bytes':(OUT/'atlantis-web.glb').stat().st_size,'web_sha256':hashlib.sha256((OUT/'atlantis-web.glb').read_bytes()).hexdigest(),'publication':'local review'}
(OUT/'v24-asset-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
