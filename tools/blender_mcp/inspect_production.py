import bpy
scene=bpy.context.scene
scene.frame_set(31)
scene.camera=bpy.data.objects['camera_beauty']
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.type='MATERIAL'
print({'frame':scene.frame_current,'fps':scene.render.fps,'camera':scene.camera.name,
       'motion_source':scene.get('motion_source'),
       'bouncer_position':list(bpy.data.objects['05_bouncing_staircase:bouncer'].matrix_world.translation),
       'physical_objects':len([o for o in scene.objects if o.get('scenescore_id')])})
