"""Deterministic V2.3 refinement; source V2.2 and all V1 assets remain untouched."""
import bpy, math, json, sys, random, hashlib, importlib.util
sys.dont_write_bytecode = True
import numpy as np
from pathlib import Path
from mathutils import Vector, noise
ROOT=Path(__file__).resolve().parents[1]
REPO=Path('/Users/eee/Desktop/code/selfy/brocade-portfolio')
OUT=ROOT/'output/gallery/master-v2-polish'; OUT.mkdir(parents=True,exist_ok=True)
WORK=ROOT/'assets/gallery/blender/working';WORK.mkdir(parents=True,exist_ok=True)
TEX=OUT/'textures';TEX.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('base',REPO/'scripts/build_atlantis_gallery_master_v2_environment.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
bpy.ops.wm.open_mainfile(filepath=str(REPO/'assets/gallery/blender/working/atlantis-gallery-master-v2-environment.blend'))
scene=bpy.context.scene; rng=random.Random(230908)
col=b.make_collection('08_V23_CRAFT_AND_ECOLOGY','COLOR_04')
artcol=b.make_collection('09_V23_CURATED_WORKS','COLOR_02')
navcol=b.make_collection('10_V23_NAVIGATION','COLOR_03')

def image_from_array(name, a, noncolor=False):
    h,w=a.shape[:2]; im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    if noncolor:im.colorspace_settings.name='Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(a,dtype=np.float32).ravel())
    im.filepath_raw=str(TEX/(name+'.png'));im.file_format='PNG';im.save();return im

def pbr(name,lo,hi,kind='stone',metal=0,rough=.72):
    n=1024; y,x=np.mgrid[0:n,0:n].astype(np.float32)/n;t=math.tau
    nr=np.random.default_rng(8723)
    f=np.zeros((n,n),np.float32)
    # Isotropic periodic fractal noise avoids the former diagonal plaid interference.
    for k,amp in [(2,.10),(5,.055),(13,.026),(31,.012),(77,.006)]:
        for wave in range(7):
            kx=int(nr.integers(-k,k+1));ky=int(nr.integers(-k,k+1))
            if kx==ky==0:kx=1
            f+=amp*np.sin(t*(kx*x+ky*y)+nr.uniform(0,math.tau))
    f=np.clip(.52+f*.45+nr.normal(0,.007,(n,n)),0,1)
    h=f*.13
    if kind=='floor':
        xx=(x*8+(np.floor(y*8)%2)*.5)%1;yy=y*8%1
        seam=(np.minimum(xx,1-xx)<.021)|(np.minimum(yy,1-yy)<.021)
        # eight-by-eight limestone tesserae with small inset bronze diamonds
        diamond=(abs(xx-.5)+abs(yy-.5)<.075)
        f=np.where(seam,.12,f);h=np.where(seam,-.25,h)
    elif kind=='sand':
        h=.13*np.sin(t*(32*y+1.8*np.sin(t*x*2)))+.02*f
        f=.6+f*.2+h*.7
    elif kind=='bronze':
        f=np.clip((f-.46)*2.2,0,1);h=f*.025
    colors=np.array(lo)[None,None,:]*(1-f[:,:,None])+np.array(hi)[None,None,:]*f[:,:,None]
    if kind=='floor':colors=np.where(diamond[:,:,None],np.array([.55,.36,.12]),colors)
    rgba=np.concatenate([colors,np.ones((n,n,1))],axis=-1)
    base=image_from_array(name+'_basecolor',rgba)
    dy,dx=np.gradient(h);norm=np.stack((-dx*20,-dy*20,np.ones_like(h)),axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
    nm=image_from_array(name+'_normal',np.concatenate((norm*.5+.5,np.ones((n,n,1))),axis=-1),True)
    # Exporter can retain G roughness / B metallic from one ORM texture.
    orm=np.ones((n,n,4));orm[:,:,1]=np.clip(rough+(f-.5)*.15,.1,1);orm[:,:,2]=metal
    if kind=='bronze':orm[:,:,2]=.85-f*.5
    rm=image_from_array(name+'_orm',orm,True)
    mat=b.material(name,(*np.mean(colors,axis=(0,1)),1),roughness=rough,metallic=metal)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    for im,inp in [(base,'Base Color')]:
        tx=nodes.new('ShaderNodeTexImage');tx.image=im;links.new(tx.outputs['Color'],bs.inputs[inp])
    tx=nodes.new('ShaderNodeTexImage');tx.image=nm;nd=nodes.new('ShaderNodeNormalMap');nd.inputs['Strength'].default_value=.7;links.new(tx.outputs['Color'],nd.inputs['Color']);links.new(nd.outputs['Normal'],bs.inputs['Normal'])
    tx=nodes.new('ShaderNodeTexImage');tx.image=rm;sep=nodes.new('ShaderNodeSeparateColor');links.new(tx.outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    return mat

print('STAGE texture authoring',flush=True)
stone=pbr('V23_HonedLimestone',(.36,.40,.33),(.76,.73,.57))
floor=pbr('V23_InlaidTesserae',(.10,.23,.24),(.43,.52,.44),'floor',.08,.61)
bronze=pbr('V23_WeatheredBronze',(.43,.29,.12),(.10,.30,.24),'bronze',.8,.38)
reef=pbr('V23_ReefLimestone',(.026,.11,.13),(.19,.32,.28),'reef',0,.9)
sand=pbr('V23_RippledSand',(.15,.30,.28),(.45,.53,.39),'sand',0,.91)
foundation=pbr('V23_BlueBasalt',(.024,.07,.085),(.10,.21,.21),'stone',.08,.76)
repl={'V2_PaleLimestone':stone,'V2_SiltMosaicFloor':floor,'V2_OxidizedBronze':bronze,'V2_SeabedRendered':sand,'V2_ReefRockRendered':reef,'V2_ReefTerraceRendered':reef,'V2_GardenRock':reef,'V2_TurquoiseSand':sand,'V2_BlueSilt':sand,'V2_RuinStone':stone,'V2_DeepTealFoundation':foundation}
for obj in list(scene.objects):
    if obj.type in {'MESH','CURVE','FONT'}:
        for slot in obj.material_slots:
            if slot.material and slot.material.name in repl:slot.material=repl[slot.material.name]
    for mod in obj.modifiers:
        if mod.type=='BEVEL':mod.segments=3
    if obj.type=='CURVE':obj.data.resolution_u=16;obj.data.bevel_resolution=3
    if obj.type=='FONT':obj.data.extrude=.002;obj.data.bevel_depth=.001
    # Remove obsolete transparent overlay planes; no unsupported procedural glTF materials.
    if 'Caustics' in obj.name or 'MosaicTick' in obj.name or 'GlassGalleryArtFrame' in obj.name or any(s in obj.name for s in ['KelpStem','KelpLeaf','OuterCoral','CoralStem','CoralBranch','SeaFan']):bpy.data.objects.remove(obj,do_unlink=True)

# Clear glass with a single transmission layer and no dithered double transparency.
for name in ('V2_ProtectedGlass','V2_WaterLightGlass'):
    mat=bpy.data.materials.get(name);bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(.62,.86,.89,1);bs.inputs['Alpha'].default_value=1
    bs.inputs['Transmission Weight'].default_value=.72;bs.inputs['Roughness'].default_value=.17;bs.inputs['IOR'].default_value=1.33
    bs.inputs['Emission Strength'].default_value=0
    mat.diffuse_color=(.62,.86,.89,1);mat.use_transparency_overlap=False
win=bpy.data.materials['V2_WarmWindow'];bs=next(n for n in win.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Alpha'].default_value=1;bs.inputs['Emission Strength'].default_value=.35;bs.inputs['Base Color'].default_value=(.48,.32,.15,1)
# Warm bays become protected plaster hanging walls, removing luminous orange rectangles.
for o in scene.objects:
    if 'GlassGalleryWarmBay' in o.name:o.data.materials.clear();o.data.materials.append(stone)

print('STAGE carved details and smooth reef geometry',flush=True)
# Real geometric refinement of reef silhouettes, not a flat-shading toggle.
for o in list(scene.objects):
    if o.type!='MESH':continue
    if any(s in o.name for s in ['BoundaryReef','GardenRock']):
        bpy.context.view_layer.objects.active=o;o.select_set(True)
        mod=o.modifiers.new('Eroded limestone silhouette','SUBSURF');mod.levels=2;mod.render_levels=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for v in o.data.vertices:v.co+=v.normal*noise.noise_vector(v.co*.8)[0]*.22
        for p in o.data.polygons:p.use_smooth=True
        o.select_set(False)
    elif any(s in o.name for s in ['Dome','Vault','Column','Finial','Fish']):
        for p in o.data.polygons:
            if len(p.vertices)<=4:p.use_smooth=True
        if ('Dome' in o.name or o.name=='V2_GlassGalleryVault') and 'Lantern' not in o.name:
            mod=o.modifiers.new('Continuous glazing curvature','SUBSURF');mod.levels=1;mod.render_levels=1

# Fine concentric cornices and dome horizontal muntins.
for label,(cx,cy),z,r in [('Archive',(-12,23),12.6,13),('RECOMPOSITION',(25,-10),7.8,5.7),('MATERIAL',(31,5),9.4,6.2),('MOOD_OBJECT',(24,21),11,6.8)]:
    rise=6.2 if label=='Archive' else 3
    for row,phi in enumerate((.35,.7,1.05)):
        pts=[(cx+r*math.sin(phi)*math.cos(i*math.tau/128),cy+r*math.sin(phi)*math.sin(i*math.tau/128),z+rise*math.cos(phi)) for i in range(129)]
        b.add_tube(f'V23_{label}_GlazingRing_{row}',pts,.037,bronze,col)
    for row,dz in enumerate((-.28,-.1,.13)):
        b.add_ellipse_band(f'V23_{label}_CarvedCornice_{row}',(cx,cy),(r+.38,r+.38),.32,z+dz,.10,stone if row==0 else bronze,col,segments=128)
    if label!='Archive':
        for rib in range(20):
            a=rib*math.tau/20;pts=[(cx+r*math.sin(i*math.pi/48)*math.cos(a),cy+r*math.sin(i*math.pi/48)*math.sin(a),z+rise*math.cos(i*math.pi/48)) for i in range(25)]
            b.add_tube(f'V23_{label}_DomeRib_{rib}',pts,.05,bronze,col)
    for i in range(72):
        a=i*math.tau/72
        b.add_box(f'V23_{label}_Dentil_{i}',(.16,.23,.18),(cx+(r+.25)*math.cos(a),cy+(r+.25)*math.sin(a),z-.42),stone,col,rotation_z=a,bevel=.02)
# Classical columns get collars and incised bronze fluting.
for o in list(scene.objects):
    if o.type=='MESH' and (('Pilaster' in o.name or 'ExteriorColumn' in o.name or 'RECOMPOSITIONColumn' in o.name or 'MATERIALColumn' in o.name or 'MOOD_OBJECTColumn' in o.name) and o.name.endswith('_Shaft')):
        x,y,z=o.location;r=max(o.dimensions.x,o.dimensions.y)/2;h=o.dimensions.z
        for k in range(8):
            a=k*math.tau/8
            b.add_tube(f'V23_Flute_{o.name}_{k}',[(x+r*.96*math.cos(a),y+r*.96*math.sin(a),z-h*.41),(x+r*.96*math.cos(a),y+r*.96*math.sin(a),z+h*.41)],.013,bronze,col)

# Continuous stone balustrade along the garden edge, leaving entry sectors clear.
for i in range(144):
    a=i*math.tau/144
    if any(abs((a-g+math.pi)%math.tau-math.pi)<.13 for g in (2.9,4.25,5.8,.8,1.9)):continue
    x,y=24*math.cos(a),18*math.sin(a)
    b.add_cylinder(f'V23_BalusterFoot_{i}',.115,.1,(x,y,3.27),stone,col,vertices=12)
    b.add_cone(f'V23_Baluster_{i}',.06,.09,.61,(x,y,3.62),stone,col,vertices=12)
    b.add_cylinder(f'V23_BalusterNeck_{i}',.115,.08,(x,y,3.94),bronze,col,vertices=12)
# Give the long gallery a stone frieze with rhythmic arch spandrels.
for side in (-1,1):
    for z in (7.6,10.9):b.add_box(f'V23_GlassHallCornice_{side}_{z}',(.32,34.2,.16),(-31+side*4.58,1.5,z),stone,col,bevel=.025)
    for i in range(8):
        y=-13.35+i*4.25
        pts=[(-31+side*4.66,y+1.74*math.cos(j*math.pi/40),10+1.05*math.sin(j*math.pi/40)) for j in range(41)]
        b.add_tube(f'V23_GlassHallArcade_{side}_{i}',pts,.075,stone,col)

print('STAGE layered marine planting',flush=True)
kelp=b.material('V23_KelpOlive',(.08,.21,.11,1),roughness=.67)
corals=[b.material('V23_CoralTerracotta',(.40,.13,.075,1),roughness=.78),b.material('V23_CoralOchre',(.46,.32,.10,1),roughness=.73),b.material('V23_CoralLavender',(.20,.20,.32,1),roughness=.8)]
# Art-directed beds stay outside the walking strips.
beds=[(-42,-17,.8,4),(-42,8,1,5),(-29,29,2,5),(-4,36,1,5),(37,26,2,5),(43,4,1,6),(37,-22,.7,5),(10,-29,.7,5),(-9,-7,3.13,2.5),(9,5,3.13,2.5),(8,-6,3.13,2.4),(-7,6,3.13,2.4)]
for bed,(cx,cy,z,spread) in enumerate(beds):
    for plant in range(15):
        x=cx+rng.uniform(-spread,spread);y=cy+rng.uniform(-spread*.7,spread*.7);h=rng.uniform(1.3,4.8) if bed<8 else rng.uniform(.8,2.3)
        pts=[(x+.25*math.sin(t*4+plant),y+.16*math.sin(t*5),z+h*t) for t in np.linspace(0,1,13)]
        b.add_tube(f'V23_KelpStem_{bed}_{plant}',pts,.025,kelp,col)
        for k in range(3,11):
            t=k/12;s=(-1)**k;verts=[]
            for j in range(9):
                q=j/8;length=.4+h*.12;xx=pts[k][0]+s*length*q
                yy=pts[k][1]+.18*math.sin(q*4+t*5);zz=pts[k][2]+length*.55*q
                w=.13*math.sin(math.pi*q)
                verts.extend([(xx,yy-w,zz),(xx,yy+w,zz+.015)])
            leaf=b.mesh_object(f'V23_KelpBlade_{bed}_{plant}_{k}',verts,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(8)],kelp,col)
            for p in leaf.data.polygons:p.use_smooth=True
    for plant in range(6):
        x=cx+rng.uniform(-spread,spread);y=cy+rng.uniform(-spread*.7,spread*.7);h=rng.uniform(.6,1.65);mat=corals[(bed+plant)%3]
        for stem in range(5):
            a=stem*2.4;end=Vector((x+.36*math.cos(a),y+.36*math.sin(a),z+h));root=Vector((x,y,z))
            b.add_tube(f'V23_Coral_{bed}_{plant}_{stem}',[root,root.lerp(end,.45),end],.045,mat,col)
            for branch in (-1,1):
                start=root.lerp(end,.6);tip=end+Vector((branch*.26*math.cos(a+1),branch*.26*math.sin(a+1),-.15))
                b.add_tube(f'V23_CoralTip_{bed}_{plant}_{stem}_{branch}',[start,start.lerp(tip,.65),tip],.029,mat,col)

# Gallery door is an open entrance with glazing overhead, not a blocking sheet.
for name in ('V2_GlassGalleryDoor','V2_ArchiveEntranceGlass'):
    o=bpy.data.objects.get(name)
    if o:bpy.data.objects.remove(o,do_unlink=True)
# Arrival-to-gallery and loop-to-pavilion connectors land on real floors.
for name,pts,width in [
 ('GlassArrival',[(-33,-20.5,.85),(-31,-18.7,3.6),(-31,-15.6,6.65)],4.6),
 ('LowerPavilion',[(22,-9,3.4),(25,-16,3.4),(25,-15.2,3.4)],3),
 ('MaterialPavilion',[(25,2,4),(28,0,4.98),(31,-.8,4.98)],2.6),
 ('MoodPavilion',[(23,16,6.2),(24,14.5,6.58)],2.8)]:
    b.add_path_strip('V23_Connector_'+name,pts,width,.25,floor,col)
# Hole through ground slab/foundation makes the lower stair usable.
for slab in ('V2_ArchiveGroundFloor','V2_ArchiveFoundation'):
    o=bpy.data.objects.get(slab)
    cutter=b.add_box('TEMP_StairWell',(2.55,8.1,3),(-6.2,24,6.1),stone,col,bevel=0)
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Open lower stairwell','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
# Shelves have compartments instead of solid blocks.
for o in list(scene.objects):
    if o.name.startswith('V2_ArchiveShelf_'):
        x,y,z=o.location;name=o.name;bpy.data.objects.remove(o,do_unlink=True)
        for dz in (-1.02,-.48,.08,.64,1.06):b.add_box('V23_'+name+str(dz),(.72,2.6,.065),(x,y,z+dz),bronze,col,bevel=.01)
        for dy in (-1.25,1.25):b.add_box('V23_'+name+'Post'+str(dy),(.72,.075,2.2),(x,y+dy,z),bronze,col,bevel=.01)
        for k in range(9):
            b.add_box('V23_ArchiveBox'+name+str(k),(.54,.27,.38),(x,y-1.0+(k%5)*.44,z-.78+(k//5)*.57),stone,col,bevel=.018)


print('STAGE spatial repairs and marine backdrop',flush=True)
# Replace the platter silhouette with a continuous, irregular reef shelf.
for name in ('V2_CampusReefPlate','V2_Seabed'):
    o=bpy.data.objects.get(name)
    if o:bpy.data.objects.remove(o,do_unlink=True)
verts=[];faces=[];grid=144
for j in range(grid+1):
    y=-100+j*220/grid
    for i in range(grid+1):
        x=-130+i*260/grid
        distance=((x/52)**2+(y/41)**2)**.5
        z=-1+.8*math.exp(-max(0,distance-1)*2)+.30*noise.noise_vector(Vector((x*.055,y*.055,1)))[0]
        verts.append((x,y,z))
for j in range(grid):
    for i in range(grid):
        a=j*(grid+1)+i;faces.append((a,a+1,a+grid+2,a+grid+1))
ground=b.mesh_object('V23_ContinuousSeabed',verts,faces,sand,col)
for poly in ground.data.polygons:poly.use_smooth=True
# Tall reefs set depth behind the pavilions, away from the circulation bands.
for i in range(36):
    a=rng.uniform(.05,math.pi-.05);x=math.cos(a)*rng.uniform(52,72);y=math.sin(a)*rng.uniform(48,60)+12
    rock=b.add_ico(f'V23_BackReef_{i}',(x,y,rng.uniform(1,4)),(rng.uniform(4,10),rng.uniform(4,9),rng.uniform(6,16)),reef,col,subdivisions=3)
    for v in rock.data.vertices:v.co+=v.normal*noise.noise_vector(v.co*.6)[0]*.65
    for poly in rock.data.polygons:poly.use_smooth=True
# Low curving raised beds make garden planting feel rooted in the architecture.
for i,(cx,cy) in enumerate(((-9,-7),(9,5),(8,-6),(-7,6))):
    b.add_ellipse_band('V23_PlanterCoping_'+str(i),(cx,cy),(3.25,2.2),.24,3.46,.25,stone,col,segments=72)
    b.add_cylinder('V23_PlanterSoil_'+str(i),3.08,.19,(cx,cy,3.25),reef,col,vertices=64,scale_xy=(1,.67))
# Carved rosette at the central installation, with an armillary bronze sculpture.
for i,r in enumerate((3.2,3.4,3.75,4.4,4.55)):
    b.add_ellipse_band('V23_RosetteRing_'+str(i),(0,0),(r,r),.045,3.16,.025,bronze,col,segments=128)
for i in range(16):
    a=i*math.tau/16
    pts=[(r*math.cos(a+.065*math.sin(r*2)),r*math.sin(a+.065*math.sin(r*2)),3.18) for r in np.linspace(3.8,4.35,12)]
    b.add_tube('V23_RosettePetal_'+str(i),pts,.025,bronze,col)
for i,tilt in enumerate((-.7,.65)):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.55,minor_radius=.055,major_segments=128,minor_segments=12,location=(0,0,8.65),rotation=(1.3,tilt,.4))
    o=bpy.context.object;o.name='V23_ArmillaryOrbit_'+str(i);o.data.materials.append(bronze);b.move_to(o,col)
# Protected radial chambers: four rooms and rear sanctum, each with an actual entrance.
for o in list(scene.objects):
    if 'Chamber' in o.name:bpy.data.objects.remove(o,do_unlink=True)
room_angles=(0,math.pi/4,3*math.pi/4,math.pi)
for i,a in enumerate(room_angles):
    radial=Vector((math.cos(a),math.sin(a),0));right=Vector((math.sin(a),-math.cos(a),0));origin=Vector((-12,23,6.4));center=origin+radial*10
    rot=a-math.pi/2
    b.add_box('V23_RadialRoomFloor_'+str(i),(5,4.8,.25),center, floor,col,rotation_z=rot,bevel=.025)
    back=center+radial*2.35+Vector((0,0,2.25))
    b.add_box('V23_RadialRoomBack_'+str(i),(5,.25,4.5),back,stone,col,rotation_z=rot,bevel=.04)
    for side in (-1,1):
        b.add_box('V23_RadialRoomSide_'+str(i)+str(side),(.22,4.8,4.5),center+right*side*2.45+Vector((0,0,2.25)),stone,col,rotation_z=rot,bevel=.025)
    # Ceiling leaves the visitor ring legible and every work sheltered.
    b.add_box('V23_RadialRoomCeiling_'+str(i),(5,4.8,.22),center+Vector((0,0,4.55)),stone,col,rotation_z=rot,bevel=.025)
    for k in range(3):
        o=bpy.data.objects.get(f'V2_ArchiveGroundArt_{i*3+k:02d}');o.location=back-radial*.25+right*(k-1)*1.5;o.location.z=8.8;o.rotation_euler.z=rot;o.dimensions=(1.25,.16,1.8)
# Upper art surfaces face the ring and have stone backings.
for i in range(8):
    o=bpy.data.objects.get(f'V2_ArchiveUpperArt_{i:02d}');a=math.atan2(o.location.y-23,o.location.x+12);o.rotation_euler.z=a-math.pi/2
    radial=Vector((math.cos(a),math.sin(a),0))
    b.add_box('V23_UpperProtectedWall_'+str(i),(2.65,.2,3.3),o.location+radial*.25-Vector((0,0,.15)),stone,col,rotation_z=a-math.pi/2,bevel=.04)
# Place pavilion works on their closed drum, clear of south-facing doorways.
for label,cx,cy,r in [('RECOMPOSITION',25,-10,5.7),('MATERIAL',31,5,6.2),('MOOD_OBJECT',24,21,6.8)]:
    for i,deg in enumerate((0,60,120,180)):
        o=bpy.data.objects.get(f'V2_{label}Art_{i}');a=math.radians(deg);o.location.x=cx+(r-.4)*math.cos(a);o.location.y=cy+(r-.4)*math.sin(a);o.rotation_euler.z=a-math.pi/2
# A protected rear wall and a side exit finish the long gallery.
b.add_box('V23_GlassGalleryRearWall',(9,.35,4.8),(-31,18.45,8.8),stone,col,bevel=.05)
b.add_arch_frame_y('V23_RearAlcove',-31,18.20,6.65,2.1,9.2,.1,bronze,col)
for side in (-1,1):
    b.add_box('V23_GlassHallBench_'+str(side),(1.0,3.2,.18),(-31+side*2.2,9.5,7.0),stone,col,bevel=.07)
# Small warm fills light the three archive levels without shadow atlas overflow.
for level,z in enumerate((4.4,9.2,14)):
    light=b.add_light('V23_ArchiveInteriorFill_'+str(level),'AREA',(-12,22,z),(1,.77,.46),550,col,size=5,target=(-12,24,z-2));light.data.use_shadow=False


print('STAGE founded masonry and pavilion arcades',flush=True)
# All elevated pavilions have structural retaining bases down to the seabed.
for label,cx,cy,z,r in [('RECOMPOSITION',25,-10,3.2,5.7),('MATERIAL',31,5,4.8,6.2),('MOOD_OBJECT',24,21,6.4,6.8)]:
    b.add_cylinder('V23_'+label+'_RetainingBase',r+.55,z-.2,(cx,cy,(z-.2)/2),foundation,col,vertices=128)
    for row in range(int(z/.65)):
        b.add_ellipse_band('V23_'+label+'_MasonryCourse_'+str(row),(cx,cy),(r+.58,r+.58),.09,.2+row*.65,.07,stone,col,segments=128)
    # The old columns were embedded in the wall; move them to the outer facade.
    for o in list(scene.objects):
        if o.name.startswith('V2_'+label+'Column_'):
            v=Vector((o.location.x-cx,o.location.y-cy,0)).normalized();o.location+=v*.72
    drum=bpy.data.objects.get('V2_'+label+'Drum')
    for i,deg in enumerate((-5,35,75,115,155,195,222)):
        a=math.radians(deg);radial=Vector((math.cos(a),math.sin(a),0));right=Vector((math.sin(a),-math.cos(a),0));c=Vector((cx,cy,z+2.5))+radial*r;rot=a-math.pi/2
        cutter=b.add_box('TEMP_Window',(1.65,2,2.8),c,stone,col,rotation_z=rot,bevel=0)
        bpy.context.view_layer.objects.active=drum;mod=drum.modifiers.new('Carved glazed opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
        b.add_box(f'V23_{label}_Window_{i}',(1.58,.055,2.75),c,bpy.data.materials['V2_ProtectedGlass'],col,rotation_z=rot,bevel=.025)
        for side in (-1,1):b.add_box(f'V23_{label}_WindowJamb_{i}_{side}',(.12,.18,2.85),c+right*side*.9+radial*.08,bronze,col,rotation_z=rot,bevel=.025)
        b.add_box(f'V23_{label}_WindowSill_{i}',(1.94,.24,.16),c+radial*.08-Vector((0,0,1.48)),stone,col,rotation_z=rot,bevel=.035)
        points=[c+right*.91*math.cos(j*math.pi/32)+Vector((0,0,1.38+.5*math.sin(j*math.pi/32)))+radial*.12 for j in range(33)]
        b.add_tube(f'V23_{label}_WindowArch_{i}',points,.075,stone,col)
    light=b.add_light('V23_'+label+'_InteriorGlow','POINT',(cx,cy,z+2.8),(1,.66,.30),430,col);light.data.shadow_soft_size=2;light.data.use_shadow=False
# Glass gallery is embedded into its reef with a coursed limestone retaining wall.
b.add_box('V23_GlassGalleryBastion',(10,35.6,5.4),(-31,1.5,2.65),foundation,col,bevel=.35)
for row in range(8):
    for side in (-1,1):
        b.add_box(f'V23_GlassBastionCourse_{row}_{side}',(.09,35.4,.07),(-31+side*5.01,1.5,.25+row*.65),stone,col,bevel=.02)
# Smooth sculptural core and lanterns are retained as curved near-field geometry.
for o in list(scene.objects):
    if o.name=='V2_GardenSculptureCore' or o.name.endswith('_Glow'):
        mod=o.modifiers.new('Polished curved glass','SUBSURF');mod.levels=2;mod.render_levels=2
        if o.type=='MESH':
            for poly in o.data.polygons:poly.use_smooth=True
# Back reefs have nested eroded forms rather than one-scale pebbles.
for o in list(scene.objects):
    if o.name.startswith('V23_BackReef_'):
        mod=o.modifiers.new('Reef surface detail','SUBSURF');mod.subdivision_type='SIMPLE';mod.levels=1
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
        for v in o.data.vertices:
            v.co+=v.normal*(noise.noise_vector(v.co*1.9)[0]*.25+noise.noise_vector(v.co*.45)[0]*.5)

sys.path.insert(0,str(Path(__file__).parent))
from atlantis_v2_finish_scene import finish
finish(b,col,stone,floor,bronze,foundation)

print('STAGE stable artwork binding',flush=True)
catalog=json.loads((REPO/'static/assets/gallery/gallery-data.json').read_text())
# Editorial featured records selected by stable catalog order; persisted as explicit IDs in manifest.
pools={r:sorted([x for x in catalog if x['room']==r and x['featured']],key=lambda x:x['order']) for r in ('color','lighting','composition','material','mood','scene')}
used=set();bindings=[]
def pick(room):
    item=next(x for x in pools[room] if x['id'] not in used);used.add(item['id']);return item
panels=sorted([o for o in scene.objects if o.type=='MESH' and o.active_material and o.active_material.name=='V2_ArtworkPlaceholder'],key=lambda o:o.name)
archive_panels=[]
for o in panels:
    if 'GlassGalleryArt_' in o.name:r='color' if '_-1_' in o.name else 'lighting'
    elif 'RECOMPOSITION' in o.name:r='composition'
    elif 'MATERIAL' in o.name:r='material'
    elif 'MOOD_OBJECT' in o.name:r='mood' if int(o.name.rsplit('_',1)[1])<2 else 'scene'
    else:archive_panels.append(o);continue
    bindings.append((o,pick(r)))
for i,o in enumerate(archive_panels):
    r=next(r for r in list(pools)[i%6:]+list(pools)[:i%6] if any(x['id'] not in used for x in pools[r]));bindings.append((o,pick(r)))
manifest=[]
for o,item in bindings:
    name=o.name;loc=o.location.copy();rot=o.rotation_euler.copy();size=o.dimensions.copy()
    narrow=min(range(3),key=lambda i:size[i]);height=min(2.05,size.z*.9);width=height*item['aspect']
    if width>3:width=3;height=width/item['aspect']
    # All curated surfaces use local XY + normal Z, with bottom-left UV origin.
    if narrow==0:
        side=-1 if loc.x<-31 else 1
        normal=Vector((-side,0,0));right=Vector((0,-side,0))
    else:
        normal=rot.to_matrix()@Vector((0,-1,0));right=rot.to_matrix()@Vector((1,0,0))
    center=loc+normal*.16;up=Vector((0,0,1))
    bpy.data.objects.remove(o,do_unlink=True)
    verts=[center-right*width/2-up*height/2,center+right*width/2-up*height/2,center+right*width/2+up*height/2,center-right*width/2+up*height/2]
    im=bpy.data.images.load(str(REPO/'static'/item['thumb'].lstrip('/')),check_existing=True)
    mat=b.material('Art_'+item['id'],(1,1,1,1),roughness=.78)
    nd=mat.node_tree.nodes.new('ShaderNodeTexImage');nd.image=im;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');mat.node_tree.links.new(nd.outputs['Color'],bs.inputs['Base Color']);mat.node_tree.links.new(nd.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.16
    obj=b.mesh_object(name,verts,[(0,1,2,3)],mat,artcol)
    uv=obj.data.uv_layers.new(name='UVMap')
    for d,v in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):d.uv=v
    obj['gallery_interactive']=True;obj['gallery_artwork_thumb']=item['thumb'];obj['gallery_artwork_id']=item['id'];obj['gallery_room']=item['room']
    for a1,a2 in [(0,1),(1,2),(2,3),(3,0)]:b.add_tube('V23_Frame_'+name+str(a1),[verts[a1]-normal*.025,verts[a2]-normal*.025],.055,bronze,artcol)
    target=center+normal*3.5
    obj['gallery_review_position']=[target.x,target.z,-target.y]
    manifest.append({k:item[k] for k in ('id','room','title','thumb','src','aspect','translation','prompt')})
    # Local spot lighting is authored at each work and exported as punctual glTF lights.
    light=b.add_light('V23_ArtLight_'+name,'SPOT',center+normal*1+up*1.3,(1,.78,.48),75,col,target=center)
    light.data.spot_size=1.65;light.data.spot_blend=.65;light.data.shadow_soft_size=.25;light.data.use_shadow=False
print('ARTWORKS',len(manifest),flush=True)
(OUT/'artworks.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))

# Navigation and target extras are authored once in Blender, consumed by web.
views=[('hero','新月园区',(-63,-72,36),(-1,6,5),40),('plan','园区全貌',(0,-38,105),(0,4,1),40),('loop','花园环路',(-18,-12,5.1),(9,6,6),30),('glass','玻璃长廊',(-31,-13,8.35),(-31,9,9),25),('archive','潮汐档案',(-12,16,8.7),(-12,25,10),23),('upper','上层回廊',(-17,19,13),(-4,28,12.2),27),('lower','下层典藏',(-11,18,4.1),(-7,27,3.6),25),('material','材质亭',(31,-.8,6.8),(31,7,7.1),26)]
for key,label,pos,target,lens in views:
    cam=b.add_camera('V23_'+key+'Camera',pos,target,lens,navcol)
    cam['gallery_nav_id']=key;cam['gallery_nav_label']=label
    marker=bpy.data.objects.new('V23_Target_'+key,None);marker.location=target;marker['gallery_nav_target_for']=key;navcol.objects.link(marker)
# Render and glTF use bright sunlit marine lighting; volume-free.
world=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');world.inputs['Color'].default_value=(.10,.31,.38,1);world.inputs['Strength'].default_value=.45
sun=b.add_light('V23_FilteredSun','SUN',(-18,-20,40),(.70,.88,1),2.0,col,target=(0,5,0));sun.data.angle=.12
for o in scene.objects:
    if o.type=='LIGHT' and o.data.type=='AREA':o.data.energy*=1.7;o.data.use_shadow=False
scene.eevee.taa_render_samples=128;scene.eevee.use_raytracing=True
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.3
scene.camera=bpy.data.objects['V23_heroCamera']
for marker in list(scene.timeline_markers):scene.timeline_markers.remove(marker)
for i,(key,*_) in enumerate(views):mk=scene.timeline_markers.new('V23 '+key,frame=1+i*20);mk.camera=bpy.data.objects['V23_'+key+'Camera']
scene.frame_end=141;scene.frame_set(1)

# Convert all curves and evaluate modifiers for identical authoring/export geometry.
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type in {'MESH','CURVE','FONT'}:o.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in scene.objects if o.select_get())
bpy.ops.object.convert(target='MESH')
print('STAGE UV projection',flush=True)
for o in scene.objects:
    if o.type!='MESH' or o.get('gallery_interactive'):continue
    if not any(m and m.name.startswith('V23_') for m in o.data.materials):continue
    uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
    for p in o.data.polygons:
        n=o.matrix_world.to_3x3()@p.normal;axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=axis]
        for li in p.loop_indices:
            v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv=(v[axes[0]]/4,v[axes[1]]/4)
scene['gallery_version']='2.3-material-craft';scene['publication_state']='local-review';scene['source_of_truth']=str(Path(__file__).resolve())
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL';area.spaces.active.shading.use_scene_world=True;area.spaces.active.shading.use_scene_lights=True
bpy.ops.object.select_all(action='DESELECT')
# Pack actual texture pixels so the Blender master stays portable.
bpy.ops.file.pack_all()
blend=WORK/'atlantis-gallery-master-v2-polish.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
tri=b.evaluated_triangles()
# Group render geometry by original collection and material to reduce web draw calls.
from collections import defaultdict
groups=defaultdict(list)
for o in list(scene.objects):
    if o.type=='MESH' and not o.get('gallery_interactive'):
        groups[(o.users_collection[0].name,tuple(m.name if m else '' for m in o.data.materials))].append(o)
for (collection,mats),objs in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    if len(objs)>1:bpy.ops.object.join()
    bpy.context.object.name='V23_Web_'+collection+'_'+(mats[0] if mats else 'default')
# Export camera-position empties; glTF cameras themselves are unnecessary.
for key,label,pos,target,lens in views:
    cam=bpy.data.objects['V23_'+key+'Camera'];empty=bpy.data.objects.new('Nav_'+key,None);empty.location=pos;navcol.objects.link(empty)
    for k in ('gallery_nav_id','gallery_nav_label'):empty[k]=cam[k];del cam[k]
# Many spotlights cost more than visible detail. Web reconstructs the active room lights from extras.
for o in list(scene.objects):
    if o.type=='LIGHT':o.hide_set(True)
glb=OUT/'atlantis-gallery-master-v2-polish.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_visible=True,export_apply=True,export_yup=True,export_extras=True,export_cameras=False,export_lights=False,export_image_format='AUTO')
(OUT/'build-audit.json').write_text(json.dumps({'version':'2.3','triangles':tri,'glb_bytes':glb.stat().st_size,'artworks':len(manifest),'navigation':len(views),'pbr_families':6,'master':str(blend),'source':str(REPO/'assets/gallery/blender/working/atlantis-gallery-master-v2-environment.blend'),'publication_state':'local-review','v1_modified':False},indent=2))
print('EXPORT_DONE',tri,glb.stat().st_size,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene=bpy.context.scene
# Clear markers while rendering different views so frame markers cannot override camera.
for marker in list(scene.timeline_markers):scene.timeline_markers.remove(marker)
scene=bpy.context.scene
for i,key in enumerate(('hero','loop','glass','archive')):
    scene.camera=bpy.data.objects['V23_'+key+'Camera'];scene.render.filepath=str(OUT/f'{i+1:02d}-{key}.png');bpy.ops.render.render(write_still=True);print('RENDER_DONE',key,flush=True)
print('COMPLETE',flush=True)
