"""Original causal workshop recipes with explicitly declared contact backends."""
import math

from modules.blender.recipes import IDS


def create_scene(config):
    import bpy
    from mathutils import Vector
    from .driver import linear_keys

    rid, variant = config['recipe'], config['variant']
    controls = ('control_drop', 'control_bounce', 'control_stack', 'control_rotated', 'control_fast', 'control_transfer', 'control_analytic_bounce', 'control_driven')
    if rid not in (*IDS, *controls):
        raise ValueError('unknown trusted recipe')
    hz, seconds = config['physics_hz'], config['seconds']
    parameters = config.get('parameters', {})
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.gravity = (0, 0, -9.81)
    scene.render.fps = hz
    scene.render.fps_base = 1
    scene.frame_start, scene.frame_end = 1, round(seconds*hz)+1
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world.color = (.22, .22, .22)
    scene.view_settings.view_transform = 'AgX'
    materials = {}
    palette = {'floor': (.48, .45, .40), 'metal': (.035, .049, .055),
               'ball': (.027, .245, .27), 'wood': (.57, .29, .08),
               'wood2': (.72, .43, .15), 'wood3': (.40, .19, .055),
               'neutral': (.45, .45, .45), 'stripe': (.78, .73, .62)}
    for name, color in palette.items():
        mat = bpy.data.materials.new('diagnostic_neutral' if name == 'neutral' else name)
        mat.diffuse_color = (*color, 1)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*color, 1)
        bsdf.inputs['Roughness'].default_value = .7 if name == 'floor' else .52
        materials[name] = mat
    specs = []
    objects = {}
    analytic_tracks = {}

    def add(name, position, *, half=None, radius=None, mode='passive', scored=False,
            role='support', material='metal', mass=1, friction=.7, restitution=.12,
            rotation=(0, 0, 0), angular_damping=.35):
        oid = rid+':'+name
        restitution = parameters.get('native_restitution', restitution)
        if radius is not None:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=radius, location=position)
        else:
            bpy.ops.mesh.primitive_cube_add(size=2, location=position)
            bpy.context.object.scale = half
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj = bpy.context.object
        obj.name = oid
        obj.rotation_euler = rotation
        obj.data.materials.append(materials[material])
        obj['scenescore_id'] = oid
        obj['scored'] = scored
        obj['sonic_identity_id'] = 'voice:'+name if scored else 'silent:'+name
        if radius:
            for poly in obj.data.polygons:
                poly.use_smooth = True
        # Shading bevel is smaller than the frozen contact tolerance.
        elif material.startswith('wood') or material == 'metal':
            bevel = obj.modifiers.new('subtle_edge', 'BEVEL')
            bevel.width = min(.002, min(half)*.005)
            bevel.segments = 2
        bpy.ops.rigidbody.object_add()
        rb = obj.rigid_body
        rb.type = 'ACTIVE' if mode in ('dynamic', 'driven') else 'PASSIVE'
        rb.kinematic = mode == 'driven'
        rb.collision_shape = 'SPHERE' if radius else 'BOX'
        rb.use_margin = True
        rb.collision_margin = .0005
        rb.mass, rb.friction, rb.restitution = mass, friction, restitution
        rb.linear_damping, rb.angular_damping = 0, angular_damping
        rb.use_deactivation = False
        spec = {'object_id': oid, 'sonic_identity_id': obj['sonic_identity_id'], 'role': role,
                'scored': scored, 'mode': mode, 'shape': 'sphere' if radius else 'box',
                'mass_kg': mass, 'friction': friction, 'restitution': restitution,
                'linear_damping': 0, 'angular_damping': angular_damping,
                'collision_margin_m': .0005, 'material': material, 'collision_enabled': True}
        if radius:
            spec['radius_m'] = radius
        else:
            spec['half_extents_m'] = list(half)
        specs.append(spec)
        objects[name] = obj
        return obj

    def drive(obj, keys):
        for t, position, rotation in keys:
            obj.location = position
            obj.rotation_euler = rotation
            obj.keyframe_insert(data_path='location', frame=1+t*hz)
            obj.keyframe_insert(data_path='rotation_euler', frame=1+t*hz)
        linear_keys(obj)

    def decor(name, pos, half, material='metal', parent=None):
        bpy.ops.mesh.primitive_cube_add(size=2, location=pos)
        obj = bpy.context.object
        obj.name = 'set:'+name
        obj.scale = half
        obj.data.materials.append(materials[material])
        if parent:
            obj.parent = parent
        return obj

    def fixed_obstacle_mechanics(ball, restitution, friction=.35):
        from .analytic import simulate_sphere
        bpy.context.view_layer.update()
        obstacles = []
        obstacle_ids = []
        for spec in specs:
            if spec['mode'] != 'passive':
                continue
            obj = bpy.data.objects[spec['object_id']]
            q = obj.matrix_world.to_quaternion()
            obstacles.append({**spec, 'position_m': list(obj.matrix_world.translation),
                              'quaternion_xyzw': [q.x,q.y,q.z,q.w]})
            obstacle_ids.append(spec['object_id'])
        spec = next(s for s in specs if s['object_id'] == ball.name)
        track = simulate_sphere(list(ball.location), [0,0,0], spec['radius_m'], obstacles, seconds,
                                hz=hz, restitution=restitution, friction=friction,
                                substeps=parameters.get('analytic_substeps',32), rolling_resistance=.02)
        # The animation is computed mechanics, never a hand-authored outcome.
        # Bullet cannot interact with this actor; its fixed obstacles are above.
        ball.rigid_body.kinematic = True
        ball.rotation_mode = 'QUATERNION'
        for row in track:
            ball.location = row['position_m']
            q = row['quaternion_xyzw']
            ball.rotation_quaternion = (q[3],*q[:3])
            ball.keyframe_insert(data_path='location',frame=1+row['tick'])
            ball.keyframe_insert(data_path='rotation_quaternion',frame=1+row['tick'])
        linear_keys(ball)
        spec.update(motion_backend='fixed-obb-sphere-mechanics-1',restitution=restitution,
                    friction=friction,rolling_resistance=.02,linear_damping=0,angular_damping=0,
                    blender_kinematic_replay=True)
        analytic_tracks[ball.name] = {'obstacle_ids':obstacle_ids,'samples':track}

    def ramp_legs(name, centre, half_x, half_y, half_z, angle):
        # Visible silent physical supports reach the actual inclined underside.
        for ix,x in enumerate((-.65*half_x,.65*half_x)):
            top=centre[2]-math.tan(angle)*x-half_z/math.cos(angle)
            for iy,y in enumerate((-.65*half_y,.65*half_y)):
                if top>0:
                    add(f'{name}-leg-{ix}-{iy}',(centre[0]+x,centre[1]+y,top/2),
                        half=(.06,.06,top/2),role='support')

    add('floor', (0, 0, -.15), half=(7, 4, .15), material='floor',
        friction=0 if rid=='control_transfer' else .85,
        restitution=1 if rid in ('control_bounce','control_transfer') else .12)
    # Visible boundary contains outcomes; it is physical and participates in QA.
    add('back_stop', (5.6, 0, .35), half=(.12, 3.7, .35), material='metal')
    add('rear_rail', (0, 3.6, .20), half=(5.7, .10, .20), material='metal')
    add('front_rail', (0, -3.6, .20), half=(5.7, .10, .20), material='metal')

    def launcher(name='projectile', y=0, target_x=.8, speed=5., radius=.28):
        angle = math.radians(parameters.get('aim_degrees', -21 if variant == 'near_miss' else 0))
        elevation=parameters.get('launcher_elevation',0)
        origin = Vector((-2.2, y, .73+elevation))
        along = Vector((math.cos(angle), math.sin(angle), 0))
        def p(x, z=.73):
            v = origin + along*x
            return (v.x, v.y, z+elevation)
        add(name+'-deck', p(.6, .40), half=(1.2, .48, .05), rotation=(0, 0, angle))
        for x in (-.35, 1.4):
            support=p(x,.175)
            add(name+'-leg-'+str(x), (support[0],support[1],(.35+elevation)/2),
                half=(.08,.35,(.35+elevation)/2),rotation=(0,0,angle))
        ball = add(name, tuple(origin), radius=radius, mode='dynamic', scored=True,
                   role='projectile', material='ball', mass=parameters.get('ball_mass', 4),
                   angular_damping=parameters.get('ball_angular_damping',.65))
        paddle = add(name+'-paddle', p(-.55, .77), half=(.075, .36, .32), mode='driven',
                     rotation=(0, 0, angle), role='mechanism', friction=.4, restitution=.12)
        end = -.75 if variant == 'no_launch' else parameters.get('paddle_end', .8)
        duration = (end+.75)/speed if variant != 'no_launch' else .3
        drive(paddle, [(0, p(-.55, .77), (0, 0, angle)), (.55, p(-.55, .77), (0, 0, angle)),
                       (.8, p(-.75, .77), (0, 0, angle)), (1.0, p(-.75, .77), (0, 0, angle)),
                       (1.0+duration, p(end, .77), (0, 0, angle)), (2.1, p(end, .77), (0, 0, angle)),
                       (3.0, p(-.75, .77), (0, 0, angle)), (seconds, p(-.75, .77), (0, 0, angle))])
        # Exposed guide and actuator housing establish the driver's physical role.
        decor(name+'-actuator', p(-.85, .24), (.42, .27, .17))
        return ball

    cases = []
    if rid == '10_projectile_tower':
        launcher(speed=parameters.get('paddle_speed', 5.0))
        for i in range(3):
            add('tower-'+str(i), (1., 0, .4+i*.8), half=(parameters.get('tower_half_x',.4),.4,.4), mode='dynamic',
                scored=True, role='tower', material=('wood', 'wood2', 'wood3')[i], mass=1.5)
        cases.append({'kind': 'stable_target', 'object_ids': [rid+':tower-'+str(i) for i in range(3)],
                      'start_s': 0, 'end_s': seconds if variant in ('near_miss', 'no_launch') else .8})
    elif rid in ('control_drop', 'control_bounce', 'control_analytic_bounce'):
        ball = add('ball', (0, 0, 2), radius=.25, mode='dynamic', scored=True, material='ball',
            restitution=1 if rid=='control_bounce' else .5,
            angular_damping=0)
        cases.append({'kind': 'free_flight', 'object_id': rid+':ball', 'start_s': .05, 'end_s': .5})
        if rid == 'control_analytic_bounce':
            next(s for s in specs if s['object_id']==rid+':floor')['restitution']=1
            fixed_obstacle_mechanics(ball,parameters.get('analytic_restitution',.55),friction=0)
    elif rid == 'control_driven':
        rail=add('rail',(0,0,.15),half=(2,.4,.15),material='metal')
        carriage=add('carriage',(-1,0,.5),half=(.25,.25,.2),mode='driven',scored=True,role='mechanism',material='wood')
        drive(carriage,[(0,(-1,0,.5),(0,0,0)),(1,(-1,0,.5),(0,0,0)),
                        (3,(1,0,.5),(0,0,0)),(seconds,(1,0,.5),(0,0,0))])
        cases.append({'kind':'stable_target','object_ids':[rail.name],'start_s':0,'end_s':seconds})
    elif rid == 'control_stack':
        for i in range(3):
            add('box-'+str(i), (0, 0, .25+i*.5), half=(.25, .25, .25), mode='dynamic', material='wood')
        cases.append({'kind': 'stable_target', 'object_ids': [rid+':box-'+str(i) for i in range(3)], 'start_s': .1, 'end_s': seconds})
    elif rid == 'control_rotated':
        for i in range(2):
            add('rod-'+str(i), (-i*.3/math.sqrt(2), i*.3/math.sqrt(2), .1), half=(1,.1,.1),
                mode='driven', rotation=(0,0,math.pi/4), material='wood', role='mechanism')
        cases.append({'kind': 'near_miss', 'object_ids': [rid+':rod-0', rid+':rod-1'], 'start_s': 0, 'end_s': seconds})
    elif rid == 'control_fast':
        add('wall', (0, 0, .7), half=(.035, .5, .7), material='wood')
        ball=add('ball', (-2,0,.6), radius=.15, mode='driven', scored=True, material='ball')
        drive(ball, [(0,(-2,0,.6),(0,0,0)),(.2,(2,0,.6),(0,0,0)),(seconds,(2,0,.6),(0,0,0))])
        cases.append({'kind': 'stable_target', 'object_ids': [rid+':wall'], 'start_s':0, 'end_s':seconds})
    elif rid == 'control_transfer':
        add('left',(-1.5,0,.28),radius=.28,mode='dynamic',scored=True,material='ball',mass=1,restitution=1,friction=0,angular_damping=0)
        add('right',(1,0,.28),radius=.28,mode='dynamic',scored=True,material='wood',mass=1,restitution=1,friction=0,angular_damping=0)
        paddle=add('paddle',(-2.,0,.3),half=(.05,.3,.25),mode='driven',restitution=0,friction=0)
        drive(paddle,[(0,(-2.,0,.3),(0,0,0)),(.5,(-2.,0,.3),(0,0,0)),(.7,(-1.4,0,.3),(0,0,0)),(seconds,(-1.4,0,.3),(0,0,0))])
        cases.append({'kind':'stable_target','object_ids':[rid+':right'],'start_s':0,'end_s':.5})
    elif rid in ('01_head_on', '02_near_miss_twins'):
        # Two supported ramp releases establish opposing motion without velocity injection.
        offset = 1.3 if rid == '02_near_miss_twins' and variant != 'contact' else 0
        for name, sign, y in [('left',1,0),('right',-1,offset)]:
            slope = sign*math.radians(12)
            add(name+'-ramp',(-sign*2.4,y,.43),half=(1.6,.5,.08),rotation=(0,slope,0))
            ramp_legs(name+'-ramp',(-sign*2.4,y,.43),1.6,.5,.08,slope)
            # Sphere tangent to the inclined top plane, not its vertical offset.
            z=.43+math.tan(math.radians(12))*1.05+(.08+.28)/math.cos(math.radians(12))+.0001
            add(name,(-sign*3.45,y,z),radius=.28,mode='dynamic',scored=True,material='ball',mass=1,
                restitution=.5, angular_damping=.98)
        cases.append({'kind':'supported_ramp_release','object_id':rid+':left','start_s':0,'end_s':seconds,
                      'verification_status':'independent ramp dynamics check required'})
    elif rid == '05_bouncing_staircase':
        for i in range(4):
            h=1.6-i*.4
            step=add('step-'+str(i),(-2.5+i*1.2,0,h/2),half=(.58,.8,h/2),scored=True,role='platform',material='wood')
            next(s for s in specs if s['object_id']==step.name)['restitution']=.8
        add('start-ramp',(-3.4,0,2.1),half=(.85,.5,.06),rotation=(0,.35,0))
        ramp_legs('start-ramp',(-3.4,0,2.1),.85,.5,.06,.35)
        ball=add('bouncer',(-3.9,0,2.63),radius=.25,mode='dynamic',scored=True,role='projectile',material='ball',restitution=.6,angular_damping=.6)
        next(s for s in specs if s['object_id']==rid+':floor')['restitution']=.8
        fixed_obstacle_mechanics(ball,.6)
        cases.append({'kind':'supported_rest','object_id':rid+':step-0','start_s':0,'end_s':seconds})
    elif rid == '06_sliding_contact':
        add('platform',(-1,0,.48),half=(2.7,.8,.12),rotation=(0,.16,0),scored=True,role='platform',material='wood')
        ramp_legs('platform',(-1,0,.48),2.7,.8,.12,.16)
        height=.48+2*math.tan(.16)+(.12+.16)/math.cos(.16)+.0001
        add('slider',(-3.,0,height),half=(.3,.3,.16),rotation=(0,.16,0),mode='dynamic',scored=True,role='slider',material='ball',friction=.08)
        cases.append({'kind':'supported_rest','object_id':rid+':platform','start_s':0,'end_s':seconds})
    elif rid == '08_domino_cascade':
        for i in range(6):
            add('tile-'+str(i),(-1.5+i*.65,0,.55),half=(.12,.35,.55),mode='dynamic',scored=True,role='cascade',material='wood')
        paddle=add('starter',(-1.9,0,.6),half=(.08,.25,.25),mode='driven',role='mechanism')
        drive(paddle,[(0,(-1.9,0,.6),(0,0,0)),(1,(-1.9,0,.6),(0,0,0)),(1.3,(-1.55,0,.6),(0,0,0)),
                      (2,(-1.55,0,.6),(0,0,0)),(3,(-1.9,0,.6),(0,0,0)),(seconds,(-1.9,0,.6),(0,0,0))])
        cases.append({'kind':'stable_target','object_ids':[rid+':tile-'+str(i) for i in range(6)],'start_s':0,'end_s':.8})
    elif rid == '07_shape_contrast':
        launcher('small',radius=.25,speed=3.0)
        add('large',(1,0,.65),half=(.65,.65,.65),scored=True,material='wood',role='target')
        add('high-ramp',(-.5,1.8,1.1),half=(2.6,.7,.1),rotation=(0,.2,0))
        ramp_legs('high-ramp',(-.5,1.8,1.1),2.6,.7,.1,.2)
        height=1.1+2*math.tan(.2)+(.1+.7)/math.cos(.2)+.0001
        add('high',(-2.5,1.8,height),radius=.7,mode='dynamic',scored=True,material='ball',angular_damping=.98)
        cases.append({'kind':'stable_target','object_ids':[rid+':large'],'start_s':0,'end_s':seconds})
    elif rid == '03_passing_ascent':
        for name, y, start, end, radius in [('ascending',-.75,.4,2.5,.4),('descending',.75,2.5,.6,.6)]:
            add(name+'-column',(-.6,y+.45,1.5),half=(.09,.09,1.5),material='metal')
            tray=add(name+'-tray',(0,y,start),half=(.7,.65,.08),mode='driven',role='mechanism')
            ball=add(name,(0,y,start+.08+radius),radius=radius,mode='driven',scored=True,material='ball',role='driven_voice')
            for obj,offset in ((tray,0),(ball,.08+radius)):
                drive(obj,[(0,(0,y,start+offset),(0,0,0)),(1,(0,y,start+offset),(0,0,0)),
                           (seconds-1,(0,y,end+offset),(0,0,0)),(seconds,(0,y,end+offset),(0,0,0))])
                next(s for s in specs if s['object_id']==obj.name)['collision_group']=name+'-assembly'
            next(s for s in specs if s['object_id']==rid+':'+name+'-column')['collision_group']=name+'-assembly'
        cases.append({'kind':'stable_target','object_ids':[rid+':floor'],'start_s':0,'end_s':seconds})
    elif rid in ('04_orbital_approach','09_breathing_crowd'):
        count=2 if rid=='04_orbital_approach' else 8
        add('hub',(0,0,.4),half=(.35,.35,.4),role='mechanism')
        for i in range(count):
            name=('orbiter-' if count==2 else 'member-')+str(i)
            phase=2*math.pi*i/count
            radius=.4 if count==2 else .27
            ball=add(name,(3*math.cos(phase),3*math.sin(phase),.55),radius=radius,mode='driven',scored=True,role='driven_voice',material='ball')
            carriage=add(name+'-carriage',(3*math.cos(phase),3*math.sin(phase),.12),half=(.38,.38,.12),mode='driven',role='mechanism')
            keys=[]
            for j in range(121):
                t=seconds*j/120
                u=min(1,max(0,(t-1)/(seconds-2)))
                ease=(1-math.cos(2*math.pi*u))/2
                r=3-1.3*ease
                theta=phase+(math.pi*2*u if count==2 else 0)
                x,y=r*math.cos(theta),r*math.sin(theta)
                keys.append((t,(x,y,.55),(0,0,theta)))
            drive(ball,keys)
            drive(carriage,[(t,(p[0],p[1],.12),rot) for t,p,rot in keys])
            # Visible vertical support couples each ball to its moving carriage.
            decor(name+'-post',(0,0,-.20),(.055,.055,.2),parent=ball)
            for obj in (ball,carriage):
                next(s for s in specs if s['object_id']==obj.name)['collision_group']=name+'-assembly'
        cases.append({'kind':'stable_target','object_ids':[rid+':hub'],'start_s':0,'end_s':seconds})

    world=scene.rigidbody_world
    world.substeps_per_frame=config['solver_substeps']
    world.solver_iterations=config['solver_iterations']
    world.time_scale=1
    world.use_split_impulse=parameters.get('split_impulse',False)
    world.point_cache.frame_start=1
    world.point_cache.frame_end=round(seconds*hz)+1
    # Broad floor markings establish the lane without becoming interaction actors.
    for y in (-1.7,1.7):
        decor('lane-'+str(y),(0,y,.001), (4.7,.018,.001), 'stripe')
    for name,location,focus,ortho in [('beauty',(8,-14,8),(-.2,0,.65),None),
                                      ('side',(0,-16,3.2),(0,0,.8),13),
                                      ('top',(0,0,18),(0,0,0),14)]:
        bpy.ops.object.camera_add(location=location)
        camera=bpy.context.object
        camera.name='camera_'+name
        camera.rotation_euler=(Vector(focus)-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.lens=44 if rid == '03_passing_ascent' and name == 'beauty' else 48
        if ortho:
            camera.data.type='ORTHO'
            camera.data.ortho_scale=ortho
    scene.camera=bpy.data.objects['camera_beauty']
    for location,power,size in [((-3,-5,9),1800,7),((4,4,6),1100,6)]:
        bpy.ops.object.light_add(type='AREA',location=location)
        light=bpy.context.object
        light.data.energy,light.data.size=power,size
        light.rotation_euler=(Vector((0,0,.5))-light.location).to_track_quat('-Z','Y').to_euler()
    scene.frame_set(1)
    return {'recipe_id':rid,'variant':variant,'seed':config['seed'],'physics_hz':hz,'render_fps':30,
            'duration_s':seconds,'gravity_m_s2':[0,0,-9.81],
            'solver':{'substeps_per_frame':config['solver_substeps'],'solver_iterations':config['solver_iterations'],
                      'use_split_impulse':world.use_split_impulse},
            'objects':specs,'validation_cases':cases,
            'require_settled_end':rid not in controls,
            'motion_mode':'fixed-obb-sphere-mechanics-1' if analytic_tracks else 'Bullet dynamics with explicitly driven mechanisms',
            'mechanics':{'model_version':'fixed-obb-sphere-mechanics-1','substeps':parameters.get('analytic_substeps',32),
                         'rolling_resistance':.02,'scope':'one sphere and fixed oriented boxes'} if analytic_tracks else None,
            '_analytic_tracks':analytic_tracks,
            'source_mode':'synthetic','approval':None}
