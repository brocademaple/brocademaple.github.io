"""Separate ascending/descending stairs and open the real upper handrail at the landings."""
import bpy,math,bmesh

def apply(b,col,stone,floor,bronze):
 scene=bpy.context.scene
 for o in list(scene.objects):
  if o.name.startswith(('V2_ArchiveUpperStairL_','V23_ArchiveUpperStairR_','V23_ArchiveRingHandrail_','V23_ArchiveBaluster_','V24_ArchiveAscendingStair_','V24_UpperStairLanding_','V24_AscendingHandrail_','V24_ArchiveRingHandrail_','V24_ArchiveBaluster_')):bpy.data.objects.remove(o,do_unlink=True)
 # The old rising exterior walk and ground slab passed through the descending stairwell.
 if not scene.get('v24_lower_wells_open'):
  for x in (-18,-6.2):
   for name in ('V2_ArchiveGroundFloor','V2_ArchiveFoundation','V2_RisingCrescentWalk'):
    o=bpy.data.objects.get(name)
    if not o:continue
    cutter=b.add_box('V24_TEMP_Well',(2.45,8.2,6.7),(x,24.35,4.75),stone,col,bevel=0)
    bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Open continuous descending stairwell','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
  scene['v24_lower_wells_open']=True
 for x in (-15.2,-8.8):
  b.add_steps('V24_ArchiveAscendingStair_'+str(x),(x,19.8,6.625),(x,30.65,11.41),1.8,28,stone,col)
  b.add_box('V24_UpperStairLanding_'+str(x),(2.0,1.2,.22),(x,30.8,11.30),floor,col,bevel=.02)
  for side in (-1,1):
   pts=[(x+side*.96,19.8,7.55),(x+side*.96,30.65,12.35)]
   b.add_tube('V24_AscendingHandrail_'+str(x)+'_'+str(side),pts,.035,bronze,col)
 for x in (-18,-6.2):
  o=bpy.data.objects['V23_LowerStairLanding_'+str(x)];o.dimensions.y=2.0;o.location.y=19.5
 # Keep a gap at each new stair and the relocated southern bridge.
 gaps=[math.radians(d) for d in (66,114,204,336)]
 def clear(a):return all(abs(math.atan2(math.sin(a-g),math.cos(a-g)))>math.radians(9) for g in gaps)
 for i in range(144):
  a=i*math.tau/144;z=12.45
  if clear(a) and clear(a+math.tau/144):
   pts=[(-12+7.85*math.cos(a+j*math.tau/288),23+7.85*math.sin(a+j*math.tau/288),z) for j in range(3)]
   b.add_tube('V24_ArchiveRingHandrail_'+str(i),pts,.045,bronze,col)
  if i%2==0 and clear(a):b.add_cylinder('V24_ArchiveBaluster_'+str(i),.03,.95,(-12+7.85*math.cos(a),23+7.85*math.sin(a),11.92),bronze,col,vertices=12)

 # Legacy path-strip winding was inward: restore outward normals for both shading and floor height.
 for o in scene.objects:
  if o.type=='MESH' and (o.name in ('V2_AccessibleArrivalRamp','V2_RisingCrescentWalk','V2_ArchiveSkyBridge','V2_ArchiveUpperBridge') or o.name.startswith('V23_Connector_')):
   bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
