"""Run only inside Blender: evaluated modifier and world-space independent area check."""
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import bpy
from modules.blender.geometry import area

mesh=bpy.data.meshes.new('independent_triangle')
mesh.from_pydata([(0,0,0),(2,0,0),(0,3,0)],[],[(0,1,2)])
obj=bpy.data.objects.new('known_triangle',mesh)
bpy.context.collection.objects.link(obj)
obj.scale=(2,3,1)
obj.location=(9,-20,5)
obj.rotation_euler=(0,0,math.pi/2)
modifier=obj.modifiers.new(name='two_triangles',type='ARRAY')
modifier.count=2
modifier.relative_offset_displace=(2,0,0)
bpy.context.view_layer.update()
ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
evaluated=ev.to_mesh()
evaluated.calc_loop_triangles()
vertices=[tuple(ev.matrix_world@v.co) for v in evaluated.vertices]
triangles=[tuple(t.vertices) for t in evaluated.loop_triangles]
actual=area(vertices,triangles)
assert len(triangles)==2
assert abs(actual-36)<1e-4,(actual,36)
ev.to_mesh_clear()
print('EVALUATED_MODIFIER_AREA_PASS',actual,'expected',36)
