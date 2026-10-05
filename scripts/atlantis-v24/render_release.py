import bpy,json,hashlib
from pathlib import Path
root=Path('/Users/eee/Desktop/works/atlantis-v24'); source=root/'atlantis-gallery-master-v2-polish.blend';bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
s.render.resolution_x=1400;s.render.resolution_y=900;s.render.resolution_percentage=100;s.eevee.taa_render_samples=128
for key,file in [('hero','01-hero.png'),('loop','02-loop.png'),('glass','03-glass.png'),('archive','04-archive.png')]:
 s.camera=bpy.data.objects['V23_'+key+'Camera'];s.render.filepath=str(root/'output'/file);bpy.ops.render.render(write_still=True);print('RENDERED',key,flush=True)
graph=bpy.context.evaluated_depsgraph_get();tri=0
for o in s.objects:
 if o.type not in ('MESH','CURVE','FONT'):continue
 e=o.evaluated_get(graph);m=e.to_mesh();m.calc_loop_triangles();tri+=len(m.loop_triangles);e.to_mesh_clear()
(root/'output'/'blender-source-audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'evaluated_triangles':tri,'engine':s.render.engine,'samples':128,'render_size':[1400,900],'render_views':['hero','loop','glass','archive'],'source_modified':False},indent=2))
print('EVALUATED_TRIANGLES',tri,flush=True)
