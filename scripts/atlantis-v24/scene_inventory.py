import bpy,json
from pathlib import Path
root=Path('/Users/eee/Desktop/works/atlantis-v24')
bpy.ops.wm.open_mainfile(filepath=str(root/'atlantis-gallery-master-v2-polish.blend'))
s=bpy.context.scene;d={'blender':bpy.app.version_string,'engine':s.render.engine,'view_transform':s.view_settings.view_transform,'look':s.view_settings.look,'exposure':s.view_settings.exposure,'objects':len(s.objects),'meshes':sum(o.type=='MESH' for o in s.objects),'materials':len(bpy.data.materials),'images':len(bpy.data.images),'collections':[c.name for c in bpy.data.collections],'cameras':[{'name':o.name,'location':list(o.location),'lens':o.data.lens,'fov':o.data.angle} for o in s.objects if o.type=='CAMERA'],'lights':[{'name':o.name,'type':o.data.type,'energy':o.data.energy,'color':list(o.data.color)} for o in s.objects if o.type=='LIGHT'],'artworks':sum(bool(o.get('gallery_interactive')) for o in s.objects),'markers':[{'name':m.name,'frame':m.frame} for m in s.timeline_markers]}
(root/'scene-inventory-2026-10-05.json').write_text(json.dumps(d,indent=2));print(json.dumps(d,indent=2))
