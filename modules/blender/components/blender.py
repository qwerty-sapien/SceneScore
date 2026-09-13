"""Optional Blender construction adapter. No scene clearing, simulation or rendering."""
import itertools


def build_component(component, *, collection=None, palette=None):
    import bpy
    scene = bpy.context.scene
    parent = collection or scene.collection
    prefix = 'component:'+component.spec.component_id
    if bpy.data.collections.get(prefix):
        raise ValueError('component collection already exists: '+prefix)
    # Validate caller-supplied materials before creating anything.
    material = (palette or {}).get(component.spec.material_role)
    if material is not None and not isinstance(material, bpy.types.Material):
        raise ValueError('palette values must be Blender materials')
    original_active = bpy.context.view_layer.objects.active
    original_selected = list(bpy.context.selected_objects)
    objects, meshes, collections = [], [], []
    result = {'component_id': component.spec.component_id, 'collision_objects': [], 'visual_objects': [],
              'physics_validated': False, 'material_role': component.spec.material_role}
    try:
        root = bpy.data.collections.new(prefix)
        collections.append(root)
        parent.children.link(root)
        for purpose, geometry in [('collision', component.collision_geometry), ('visual', component.visual_geometry)]:
            layer = bpy.data.collections.new(prefix+':'+purpose)
            collections.append(layer)
            root.children.link(layer)
            for box in geometry:
                name = prefix+':'+purpose+':'+box.part_id
                mesh = bpy.data.meshes.new(name)
                meshes.append(mesh)
                vertices = [tuple(h*s for h, s in zip(box.half_extents_m, signs))
                            for signs in itertools.product((-1, 1), repeat=3)]
                faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
                mesh.from_pydata(vertices, [], faces)
                mesh.update()
                obj = bpy.data.objects.new(name, mesh)
                objects.append(obj)
                layer.objects.link(obj)
                obj.location = box.position_m
                obj.rotation_mode = 'QUATERNION'
                x, y, z, w = box.quaternion_xyzw
                obj.rotation_quaternion = (w, x, y, z)
                obj['component_id'] = component.spec.component_id
                obj['part_id'] = box.part_id
                obj['geometry_role'] = purpose
                obj['material_role'] = component.spec.material_role
                if purpose == 'collision':
                    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
                        bpy.ops.rigidbody.object_add()
                    obj.rigid_body.type = 'PASSIVE'
                    obj.rigid_body.collision_shape = 'BOX'
                    obj.rigid_body.friction = component.spec.friction
                    obj.rigid_body.restitution = component.spec.restitution
                    obj.rigid_body.use_margin = True
                    obj.rigid_body.collision_margin = 0.
                    obj.hide_render = True
                    obj.display_type = 'WIRE'
                else:
                    if material:
                        obj.data.materials.append(material)
                    if component.spec.bevel_m:
                        modifier = obj.modifiers.new('bounded-visual-bevel', 'BEVEL')
                        modifier.width = component.spec.bevel_m
                        modifier.segments = 2
                result[purpose+'_objects'].append(obj.name)
        bpy.context.view_layer.update()
        return result
    except BaseException:
        for obj in reversed(objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for layer in reversed(collections):
            bpy.data.collections.remove(layer)
        raise
    finally:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in original_selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = original_active
