"""Incremental V2.4: portable PBR textures and navigation from the Blender master."""
import bpy,math,json,sys,re,importlib.util
sys.dont_write_bytecode=True
import numpy as np
from pathlib import Path
from mathutils import Vector
from collections import defaultdict
REPO=Path('/Users/eee/Desktop/code/selfy/brocade-portfolio')
ROOT=Path('/Users/eee/Desktop/works/atlantis-v24')
OUT=ROOT/'output';TEX=OUT/'textures';TEX.mkdir(parents=True,exist_ok=True)
SOURCE=REPO/'assets/gallery/blender/working/atlantis-gallery-master-v2-polish.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
spec=importlib.util.spec_from_file_location('base',REPO/'scripts/build_atlantis_gallery_master_v2_environment.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
col=b.make_collection('11_V24_SURFACES_AND_ACCESS','COLOR_04')

def texture(name,kind,n=2048):
 y,x=np.mgrid[0:n,0:n].astype(np.float32)/n;rng=np.random.default_rng(240908)
 fine=rng.normal(0,1,(n,n)).astype(np.float32)
 cloud=np.zeros((n,n),np.float32)
 for k,a in [(1,.11),(3,.08),(9,.045),(27,.025),(81,.012)]:
  for _ in range(5):
   kx,ky=rng.integers(-k,k+1,2);cloud+=a*np.sin(math.tau*(kx*x+ky*y)+rng.uniform(0,math.tau))
 cloud=np.clip(.5+cloud,0,1)
 h=.025*cloud+.002*fine;rough=np.full((n,n),.65);metal=np.zeros((n,n));ao=np.ones((n,n))
 if kind in ('stone','ashlar'):
  veins=np.sin(math.tau*(y*24+cloud*.8))*.5+.5
  tone=.86+cloud*.10+fine*.014-veins*.025
  rgb=tone[:,:,None]*np.array([.70,.64,.49])
  pores=fine<-1.8;h-=pores*.012;rgb[pores]*=.91
  rough=.58+cloud*.16+pores*.12
  if kind=='ashlar':
   row=np.floor(y*8);u=(x*4+(row%2)*.5)%1;v=y*8%1
   edge=np.minimum(np.minimum(u,1-u)/4,np.minimum(v,1-v)/8)
   joint=edge<.0017;bevel=np.clip(edge/.006,0,1)
   block=(np.sin(np.floor(x*4+(row%2)*.5)*13.37+row*4.74)*.5+.5)
   rgb*= (.91+block*.12)[:,:,None];rgb[joint]=[.22,.25,.22]
   h+=bevel*.10;ao=.7+.3*bevel;rough[joint]=.94
 elif kind=='paving':
  u=x*4%1;v=y*4%1;dx=abs(u-.5);dy=abs(v-.5)
  corner=dx+dy>.73;border=abs(dx+dy-.73)<.014
  edge=np.minimum(np.minimum(u,1-u),np.minimum(v,1-v))
  joint=(edge<.008)|(abs(dx+dy-.73)<.007)
  stone=np.array([.60,.57,.45]);teal=np.array([.055,.19,.19]);gold=np.array([.44,.30,.12])
  rgb=np.where(corner[:,:,None],teal,stone)*( .89+cloud*.15+fine*.015)[:,:,None]
  rgb[border]=gold;rgb[joint]=[.055,.09,.085]
  # Tiny tesserae within the inset dark diamond give it a hand-laid mosaic surface.
  tiny=corner&((u*16%1<.06)|(v*16%1<.06));rgb[tiny]*=.72
  h+=np.where(joint,-.07,.025);h[tiny]-=.008
  rough=np.where(corner,.47,.62)+cloud*.07;metal[border]=.65;ao[joint]=.7
 elif kind=='gravel':
  # Irregular Voronoi pebbles, no painted oversized noise blotches.
  size=32;gx=x*size;gy=y*size;ix=np.floor(gx);iy=np.floor(gy);nearest=np.full_like(x,1e4);second=nearest.copy();ident=np.zeros_like(x)
  offsets=rng.random((size,size,2))*.7+.15
  for dy in (-1,0,1):
   for dx in (-1,0,1):
    ax=(ix.astype(int)+dx)%size;ay=(iy.astype(int)+dy)%size
    ox=offsets[ay,ax,0]+ix+dx;oy=offsets[ay,ax,1]+iy+dy
    d=(gx-ox)**2+(gy-oy)**2;better=d<nearest
    second=np.where(better,nearest,np.minimum(second,d));ident=np.where(better,(ax*17+ay*37)%31/31,ident);nearest=np.minimum(nearest,d)
  grout=np.clip((second-nearest)*4,0,1);h=.05*grout+.003*fine
  rgb=(.76+ident*.30)[:,:,None]*np.array([.25,.34,.27]);rgb*= (.6+.4*grout)[:,:,None];rough=.82+cloud*.10;ao=.65+.35*grout
 dy,dx=np.gradient(h);normal=np.stack((-dx*n/18,-dy*n/18,np.ones_like(h)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
 arrays={'basecolor':np.clip(rgb,0,1),'normal':normal*.5+.5,'orm':np.stack((ao,rough,metal),axis=-1)}
 imgs={}
 for suffix,data in arrays.items():
  im=bpy.data.images.new(name+'_'+suffix,width=n,height=n,alpha=False)
  if suffix!='basecolor':im.colorspace_settings.name='Non-Color'
  im.pixels.foreach_set(np.concatenate((data,np.ones((n,n,1))),axis=-1).astype(np.float32).ravel());im.filepath_raw=str(TEX/(name+'_'+suffix+'.png'));im.file_format='PNG';im.save();imgs[suffix]=im
 mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 tx=nodes.new('ShaderNodeTexImage');tx.image=imgs['basecolor'];links.new(tx.outputs['Color'],bs.inputs['Base Color'])
 tx=nodes.new('ShaderNodeTexImage');tx.image=imgs['normal'];nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.75;links.new(tx.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
 tx=nodes.new('ShaderNodeTexImage');tx.image=imgs['orm'];sep=nodes.new('ShaderNodeSeparateColor');links.new(tx.outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 # glTF exporter recognizes the occlusion socket in this standard group.
 group=bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
 if not any(s.name=='Occlusion' for s in group.interface.items_tree):group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
 node=nodes.new('ShaderNodeGroup');node.node_tree=group;links.new(sep.outputs['Red'],node.inputs['Occlusion'])
 return mat
print('AUTHORING PBR',flush=True)
stone=texture('V24_HonedTravertine','stone');ashlar=texture('V24_CoursedTravertine','ashlar');floor=texture('V24_OpusPaving','paving');gravel=texture('V24_GardenPebbles','gravel',1024)
for o in scene.objects:
 if o.type!='MESH':continue
 for slot in o.material_slots:
  if slot.material and slot.material.name=='V23_HonedLimestone':slot.material=ashlar if any(w in o.name for w in ['Wall','Back','Bastion','Drum','VaultSide','CabinetSide']) else stone
  elif slot.material and slot.material.name=='V23_InlaidTesserae':slot.material=floor
 if o.name=='V2_GardenPlinth':o.data.materials.clear();o.data.materials.append(gravel)
# The old upper bridge ran through the central light chamber. Shift its deck and rails south.
for o in scene.objects:
 if o.name=='V2_ArchiveUpperBridge' or 'V23_UpperBridgeRail' in o.name:o.location.y-=3.2
# Connect the inner garden across its dry moat to the actual visitor loop.
for side in (-1,1):b.add_box('V24_GardenCrossing_'+str(side),(4.4,2.2,.25),(side*19.2,0,3.22),floor,col,bevel=.035)
# A broad staircase connects the garden level to the archive forecourt.
b.add_steps('V24_GardenArchiveStair',(-12,-1,3.1),(-12,5.0,5.31),3.8,14,stone,col)
b.add_box('V24_ArchiveThreshold',(5.6,2.9,.25),(-12,10.5,6.52),floor,col,bevel=.025)
# Safe eye-level entry marker; the former overview faced directly across a void.
cam=bpy.data.objects['V23_loopCamera'];cam.location=(-16.5,-10.3,5.06)
bpy.data.objects['V23_Target_loop'].location=(-9,-14.2,4.95)
# Upper view now starts on the real southern ring.
bpy.data.objects['V23_upperCamera'].location=(-17,15.0,13.06)
bpy.data.objects['V23_Target_upper'].location=(-10,14.0,12.8)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from access_v24 import apply as apply_access
apply_access(b,col,stone,floor,bpy.data.materials['V23_WeatheredBronze'])
# World-metre planar UVs keep masonry courses horizontal and at consistent physical scale.
for o in scene.objects:
 if o.type=='MESH' and not o.get('gallery_interactive') and any(m and m.name.startswith('V24_') for m in o.data.materials):
  uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
  for p in o.data.polygons:
   normal=o.matrix_world.to_3x3()@p.normal;axis=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=axis]
   for li in p.loop_indices:
    v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/4,v[axes[1]]/4)
# Evaluate newly authored bevels just as the source master does.
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
 if o.type in {'MESH','CURVE','FONT'}:o.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in scene.objects if o.select_get());bpy.ops.object.convert(target='MESH');scene.view_layers[0].update()
print('EXPORT NAVIGATION',flush=True)
floors=[];obstacles=[];floor_names=[];obstacle_names=[]
walk_words=('Floor','Stair','VisitorLoop','RisingCrescentWalk','AccessibleArrivalRamp','SkyBridge','UpperBridge','UpperRing','Connector_','Landing','ArrivalTerrace','ArrivalThreshold','GardenPlinth','GardenCrossing','ArchiveThreshold')
block_words=('Wall','Drum','Column','Pilaster','Baluster','Rail','Bench','ConservationTable','RadialRoomBack','RadialRoomSide','VaultBack','VaultSide','CabinetBack','CabinetSide','LightChamber','WaterLightCore','Ceiling','Roof')
for o in scene.objects:
 if o.type!='MESH':continue
 isfloor=any(w in o.name for w in walk_words) and not any(w in o.name for w in ('Rail','Support','Baluster'))
 isblock=not isfloor and any(w in o.name for w in block_words) and not any(w in o.name for w in ('Flute','Cornice','Art','Frame','Glow','LightChamberRing','DomeRib'))
 if not(isfloor or isblock):continue
 o['gallery_walk_surface']=isfloor;o['gallery_walk_obstacle']=isblock
 o.data.calc_loop_triangles();verts=[o.matrix_world@v.co for v in o.data.vertices]
 count=0
 for t in o.data.loop_triangles:
  vs=[verts[i] for i in t.vertices];normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized()
  if isfloor and normal.z<.55:continue
  coords=[round(c,5) for v in vs for c in (v.x,v.z,-v.y)]
  (floors if isfloor else obstacles).append(coords);count+=1
 if count:(floor_names if isfloor else obstacle_names).append(o.name)
spawns={}
for o in scene.objects:
 if o.get('gallery_nav_id'):
  key=o['gallery_nav_id'];v=o.matrix_world.translation;t=bpy.data.objects['V23_Target_'+key].matrix_world.translation
  spawns[key]={'position':[v.x,v.z,-v.y],'target':[t.x,t.z,-t.y]}
(OUT/'navigation.json').write_text(json.dumps({'version':2,'coordinate_system':'glTF Y-up','eyeHeight':1.65,'radius':.24,'maxStep':.34,'floors':floors,'obstacles':obstacles,'spawns':spawns,'floor_objects':floor_names,'obstacle_objects':obstacle_names},separators=(',',':')))
scene['gallery_version']='2.4-surface-navigation';scene['source_of_truth']=str(Path(__file__).resolve());scene['publication_state']='local-review'
bpy.ops.object.select_all(action='DESELECT');bpy.ops.file.pack_all()
blend=ROOT/'atlantis-gallery-master-v2-polish.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
tri=sum(len(o.data.loop_triangles) for o in scene.objects if o.type=='MESH')
print('SAVE_DONE',len(floors),len(obstacles),flush=True)
# Export unchanged art objects separately; merge only render objects sharing materials.
groups=defaultdict(list)
for o in list(scene.objects):
 if o.type=='MESH' and not o.get('gallery_interactive'):groups[(o.users_collection[0].name,tuple(m.name if m else '' for m in o.data.materials))].append(o)
for (collection,mats),objs in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0]
 if len(objs)>1:bpy.ops.object.join()
 bpy.context.object.name='V24_Web_'+collection+'_'+(mats[0] if mats else 'default')
for o in list(scene.objects):
 if o.get('gallery_nav_id') and o.type=='CAMERA':
  empty=bpy.data.objects.new('Nav_'+o['gallery_nav_id'],None);empty.matrix_world=o.matrix_world;col.objects.link(empty)
  for key in ('gallery_nav_id','gallery_nav_label'):empty[key]=o[key];del o[key]
 if o.type=='LIGHT':o.hide_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'atlantis-gallery-master-v2-polish.glb'),export_format='GLB',use_visible=True,export_apply=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False,export_image_format='AUTO')
print('EXPORT_DONE',flush=True)
# Short render reviews share the same material source as the browser.
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
for marker in list(scene.timeline_markers):scene.timeline_markers.remove(marker)
scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.eevee.taa_render_samples=64
for key,name in [('loop','02-loop.png'),('glass','03-glass.png'),('hero','01-hero.png')]:
 scene.camera=bpy.data.objects['V23_'+key+'Camera'];scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
print('RENDER_DONE',flush=True)
