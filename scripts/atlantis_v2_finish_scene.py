"""Final structural/optical pass, shared by fresh builds and incremental correction."""
import bpy,math
from mathutils import Vector

def finish(b,col,stone,floor,bronze,foundation):
    scene=bpy.context.scene
    # Thin clear light chamber: avoid the formerly opaque luminous cylinder.
    mat=bpy.data.materials['V2_WaterLightGlass'];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(.12,.47,.54,1);bs.inputs['Alpha'].default_value=.09;bs.inputs['Transmission Weight'].default_value=.12;bs.inputs['Roughness'].default_value=.08;bs.inputs['Emission Strength'].default_value=0
    light=bpy.data.objects.get('V2_LightShaftGlow')
    if light:light.data.energy=40
    for i in range(8):
        a=i*math.tau/8
        b.add_tube('V23_LightChamberRib_'+str(i),[(-12+1.47*math.cos(a),23+1.47*math.sin(a),2.4),(-12+1.47*math.cos(a),23+1.47*math.sin(a),18.7)],.024,bronze,col)
    for z in (2.4,6.65,11.4,18.7):
        b.add_ellipse_band('V23_LightChamberRing_'+str(z),(-12,23),(1.51,1.51),.055,z,.07,bronze,col,segments=96)
    o=bpy.data.objects.get('V2_ArchiveUpperRailing')
    if o:bpy.data.objects.remove(o,do_unlink=True)
    pts=[]
    for i in range(145):
        a=i*math.tau/144;pts.append((-12+7.85*math.cos(a),23+7.85*math.sin(a),12.45))
        if i%2==0 and abs(math.sin(a))>.15:
            b.add_cylinder('V23_ArchiveBaluster_'+str(i),.035,.95,(-12+7.85*math.cos(a),23+7.85*math.sin(a),11.92),bronze,col,vertices=12)
    # Two half rails leave actual openings at the bridge, instead of fencing it off.
    for i,(start,end) in enumerate(((.16,math.pi-.16),(math.pi+.16,math.tau-.16))):
        pts=[(-12+7.85*math.cos(start+(end-start)*j/72),23+7.85*math.sin(start+(end-start)*j/72),12.45) for j in range(73)]
        b.add_tube('V23_ArchiveRingHandrail_'+str(i),pts,.055,bronze,col)
    # Twin ascending and descending routes, each with a floor landing.
    b.add_steps('V23_ArchiveUpperStairR',(-5.5,21,6.65),(-5.5,28.5,11.41),2.1,24,stone,col)
    b.add_steps('V23_ArchiveLowerStairL',(-18,27.8,2.425),(-18,20.3,6.625),2.1,22,stone,col)
    for name in ('V2_ArchiveGroundFloor','V2_ArchiveFoundation'):
        o=bpy.data.objects.get(name)
        cutter=b.add_box('TEMP_LeftStairOpening',(2.45,6.7,3),(-18,24.65,6.1),stone,col,bevel=0)
        bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Open left lower stairwell','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    for x in (-18,-6.2):b.add_box('V23_LowerStairLanding_'+str(x),(2.5,1.3,.23),(x,19.55,6.53),floor,col,bevel=.015)
    # Archive vaults form three separate rooms. Their doors face the circular public aisle.
    for i,a in enumerate((0,math.pi/2,math.pi)):
        radial=Vector((math.cos(a),math.sin(a),0));right=Vector((math.sin(a),-math.cos(a),0));center=Vector((-12,23,2.2))+radial*9;rot=a-math.pi/2
        b.add_box('V23_LowerVaultFloor_'+str(i),(4.4,3.7,.2),center,floor,col,rotation_z=rot,bevel=.02)
        b.add_box('V23_LowerVaultBack_'+str(i),(4.4,.22,3.6),center+radial*1.75+Vector((0,0,1.8)),foundation,col,rotation_z=rot,bevel=.02)
        for side in (-1,1):b.add_box(f'V23_LowerVaultSide_{i}_{side}',(.2,3.7,3.6),center+right*side*2.1+Vector((0,0,1.8)),stone,col,rotation_z=rot,bevel=.02)
        b.add_box('V23_LowerVaultLintel_'+str(i),(4.4,.3,.35),center-radial*1.8+Vector((0,0,3.4)),bronze,col,rotation_z=rot,bevel=.03)
    # Two upper cabinets have floors, sides, and a door opening onto the ring.
    for side in (-1,1):
        cx=-12+side*8.3;cy=25.9
        b.add_box('V23_UpperCabinetFloor_'+str(side),(3.5,4,.2),(cx,cy,11.23),floor,col,bevel=.025)
        b.add_box('V23_UpperCabinetBack_'+str(side),(3.5,.18,3.3),(cx,cy+1.9,13),stone,col,bevel=.025)
        for sx in (-1,1):b.add_box(f'V23_UpperCabinetSide_{side}_{sx}',(.18,4,3.3),(cx+sx*1.65,cy,13),stone,col,bevel=.025)
    # Bridge railings keep visitors away from the light void.
    for side in (-1,1):
        b.add_tube('V23_UpperBridgeRail_'+str(side),[(-20,23+side*1.05,12.55),(-13.65,23+side*1.05,12.55)],.045,bronze,col)
        b.add_tube('V23_UpperBridgeRailB_'+str(side),[(-10.35,23+side*1.05,12.55),(-4,23+side*1.05,12.55)],.045,bronze,col)
    scene['archive_circulation_note']='Two upward and two downward stairs; three lower vault rooms; two upper cabinets; source-authored bridge and paired camera markers.'
