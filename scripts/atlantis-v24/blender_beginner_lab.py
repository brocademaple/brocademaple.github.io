"""A separate learning scene: three columns, a display wall, camera and light. Never opens the gallery master."""
import bpy, math
from pathlib import Path
from mathutils import Vector
root=Path('/Users/eee/Desktop/works/atlantis-v24/tutorial');root.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC'
stone=bpy.data.materials.new('Lab_Limestone');stone.diffuse_color=(.65,.60,.46,1);stone.use_nodes=True;stone.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.65
bronze=bpy.data.materials.new('Lab_Bronze');bronze.use_nodes=True;bs=bronze.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.40,.24,.07,1);bs.inputs['Metallic'].default_value=.75;bs.inputs['Roughness'].default_value=.35
col=bpy.data.collections.new('LAB_Architecture');scene.collection.children.link(col)
def move(o,name,mat):
 o.name=name;o.data.materials.append(mat)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o)
 return o
def box(name,loc,scale,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=move(bpy.context.object,name,mat);o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=o.modifiers.new('Small_Edge_Bevel','BEVEL');mod.width=.04;mod.segments=2;return o
box('Lab_Floor',(0,0,-.15),(9,7,.3),stone)
box('Lab_DisplayWall',(0,2,1.8),(8,.3,3.6),stone)
for i,x in enumerate((-3,0,3)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.22,depth=3.2,location=(x,0,1.6));move(bpy.context.object,'Lab_Column_'+str(i+1),stone)
box('Lab_ArtworkPlane',(0,1.80,1.9),(1.8,.04,1.2),bronze)
bpy.ops.object.light_add(type='AREA',location=(-3,-3,7));lamp=bpy.context.object;lamp.name='Lab_KeyLight';lamp.data.energy=1200;lamp.data.shape='DISK';lamp.data.size=5;lamp.rotation_euler=(Vector((0,0,1.5))-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(9,-12,8));cam=bpy.context.object;cam.name='Lab_Camera';cam.rotation_euler=(Vector((0,.6,1.4))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=40;scene.camera=cam
scene.render.engine='BLENDER_EEVEE_NEXT';scene.world.color=(.14,.20,.23);scene.render.resolution_x=960;scene.render.resolution_y=640;scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(root/'blender-beginner-lab.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'blender-beginner-lab.glb'),export_format='GLB',export_apply=True,export_extras=True)
print('PASS: separate beginner .blend and .glb saved')
