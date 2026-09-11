"""Ten original abstract, scripted recipes. Normalized linear keys are authoritative.

No dynamics solver: collisions are geometric choreography, not measured forces.
"""
import math
import random

IDS = ('01_head_on','02_near_miss_twins','03_passing_ascent','04_orbital_approach',
       '05_bouncing_staircase','06_sliding_contact','07_shape_contrast','08_domino_cascade',
       '09_breathing_crowd','10_projectile_tower')


def recipe(recipe_id, seed=42, variant='default'):
    if recipe_id not in IDS or variant not in ('default', 'near_miss', 'contact'):
        raise ValueError('unknown recipe or variant')
    if variant != 'default' and recipe_id not in (IDS[1], IDS[9]):
        raise ValueError('matched variants are supported only for twins and hero')
    objects = []
    rng = random.Random(seed)
    def add(name, keys, radius=.5, half=None, role='voice'):
        objects.append(dict(object_id=recipe_id+':'+name, sonic_identity_id='voice:'+name,
                            shape='box' if half else 'sphere', radius=radius, half=half,
                            role=role, keys=keys, color=[.15+rng.random()*.65 for _ in range(3)]))
    if recipe_id == IDS[9]:  # Hero first: hold, deliberate approach, contact, collapse, sparse ending.
        miss = variant == 'near_miss'
        y = -1.5 if miss else 0
        add('projectile', [(0,(-6,y,1)),(.12,(-6,y,1)),(.42,(-1,y,1)),
                          (.50,(-1,y,1)),(.72,((-1 if not miss else 6),y,1)),
                          (1,((-1 if not miss else 6),y,1))], role='projectile')
        for i in range(3):
            z = 1+1.05*i
            keys = [(0,(0,0,z)),(.5+i*.035,(0,0,z))]
            if not miss:
                keys += [(.74+i*.025,(1.5+i*1.05,0,.5)),(.86+i*.015,(1.5+i*1.05,0,.6)),
                         (.96,(1.5+i*1.05,0,.5))]
            keys += [(1, keys[-1][1])]
            add('tower-'+str(i), keys, half=(.5,.5,.5), role='tower')
    elif recipe_id == IDS[0]:
        for name, sign in [('left',-1),('right',1)]:
            add(name, [(0,(sign*4,0,1)),(.45,(sign*.5,0,1)),(.55,(sign*.5,0,1)),(1,(sign*4,0,1))])
    elif recipe_id == IDS[1]:
        offset = 0 if variant == 'contact' else 1.3
        add('left',[(0,(-4,0,1)),(1,(4,0,1))])
        add('right',[(0,(4,offset,1)),(1,(-4,offset,1))])
    elif recipe_id == IDS[2]:
        add('ascending',[(0,(-4,0,.6)),(1,(4,0,4))],radius=.4)
        add('descending',[(0,(4,1.4,4)),(1,(-4,1.4,.6))],radius=.6)
    elif recipe_id == IDS[3]:
        for j in range(2):
            keys=[]
            for i in range(65):
                u=i/64
                r=1.1+2.4*abs(2*u-1)
                theta=2*math.pi*u+j*math.pi
                keys.append((u,(r*math.cos(theta),r*math.sin(theta),1+j*.3)))
            add('orbiter-'+str(j), keys)
    elif recipe_id == IDS[4]:
        keys=[(0,(-4,0,4.5))]
        for i in range(4):
            x=-3+2*i
            z=3-i*.65
            add('step-'+str(i),[(0,(x,0,z-.25)),(1,(x,0,z-.25))],half=(.85,1,.25),role='platform')
            keys += [(.15+i*.22,(x,0,z+.5)),(.25+i*.22,(x+.6,0,z+1.2))]
        keys += [(1,(4,0,1.5))]
        add('bouncer',keys,role='projectile')
    elif recipe_id == IDS[5]:
        add('platform',[(0,(0,0,0)),(1,(0,0,0))],half=(5,1,.2),role='platform')
        add('slider',[(0,(-4,0,2)),(.2,(-3,0,.7)),(.75,(3,0,.7)),(1,(4,0,2))])
    elif recipe_id == IDS[6]:
        add('small',[(0,(-4,0,1)),(.5,(-1.25,0,1)),(1,(-4,0,1))],radius=.25)
        add('large',[(0,(0,0,1)),(1,(0,0,1))],half=(1,1,1))
        add('high',[(0,(-4,0,4)),(1,(4,0,4))],radius=.7)
    elif recipe_id == IDS[7]:
        # Upright tiles slide into each neighbour, then drop: exact AABB geometry, no fake physics.
        for i in range(6):
            start=.1+i*.10
            x=-4+i*1.5
            add('tile-'+str(i),[(0,(x,0,1)),(start,(x,0,1)),
                (start+.10,(x+1.1,0,1)),(start+.18,(x+1.1,0,.4)),(1,(x+1.1,0,.4))],half=(.2,.6,1),role='cascade')
    elif recipe_id == IDS[8]:
        for i in range(8):
            theta=2*math.pi*i/8
            keys=[]
            for u,r in [(0,4),(.45,1.5),(.55,1.5),(1,4)]:
                keys.append((u,(r*math.cos(theta),r*math.sin(theta),1+(i%2)*.3)))
            add('member-'+str(i),keys,radius=.35)
    # Seed changes timing as well as color, while preserving event order and geometry.
    exponent=1.0 if seed==42 else .9+random.Random(seed).random()*.2
    for spec in objects:
        spec['keys']=[(u**exponent,p) for u,p in spec['keys']]
    return objects


def position(spec, u):
    keys=spec['keys']
    for (t0,p0),(t1,p1) in zip(keys,keys[1:]):
        if t0 <= u <= t1:
            w=(u-t0)/(t1-t0) if t1>t0 else 0
            return tuple(a+(b-a)*w for a,b in zip(p0,p1))
    return keys[-1][1]
