import math
from pathlib import Path
import pytest
from modules.blender.geometry import area, gap, pair_timeline, sphere_sweep
from modules.blender.recipes import IDS, position, recipe

SPHERE={'shape':'sphere','radius':1}


def test_exact_sphere_touch_and_tunnelling():
    assert sphere_sweep((-5,0,0),(5,0,0),(0,0,0),(0,0,0),2)==pytest.approx(.3)
    assert sphere_sweep((-5,3,0),(5,3,0),(0,0,0),(0,0,0),2) is None
    rows,events=pair_timeline(SPHERE,SPHERE,[(0,(-5,0,0),(0,0,0)),(1,(5,0,0),(0,0,0))])
    assert len(events)==1 and events[0]['event_type']=='collision'
    assert events[0]['onset_s']==pytest.approx(.3)


def test_near_miss_independent_ground_truth():
    samples=[(i/10,(-5+i,3,0),(0,0,0)) for i in range(11)]
    rows,events=pair_timeline(SPHERE,SPHERE,samples)
    misses=[e for e in events if e['event_type']=='near_miss']
    assert len(misses)==1
    assert misses[0]['sample']['gap']==pytest.approx(1)
    assert misses[0]['sample']['t']==.5
    assert misses[0]['onset_s']==0 and misses[0]['duration_s']==1
    assert not any(e['event_type'].startswith('contact') for e in events)


def test_constant_separation_no_events():
    _,events=pair_timeline(SPHERE,SPHERE,[(i,(i,0,0),(i,3,0)) for i in range(4)])
    assert events==[]


def test_continuous_contact_deduplicated():
    _,events=pair_timeline(SPHERE,SPHERE,[(i,(0,0,0),(d,0,0)) for i,d in enumerate([3,2,2,2,3])])
    kinds=[e['event_type'] for e in events]
    assert kinds.count('contact_onset')==kinds.count('contact_sustain')==kinds.count('contact_release')==1
    assert 'near_miss' not in kinds


def test_world_area_scaling_rotation_translation_and_nonuniform_scale():
    verts=[(0,0,0),(2,0,0),(0,3,0)]
    triangles=[(0,1,2)]
    assert area(verts,triangles)==3
    assert area([(x*4,y*4,z*4) for x,y,z in verts],triangles)==48
    assert area([(-y+9,x-20,z+5) for x,y,z in verts],triangles)==3
    assert area([(x*2,y*3,z) for x,y,z in verts],triangles)==18


def test_sphere_plane_box_contact_and_separation():
    box={'shape':'box','half':(5,5,.2)}
    assert gap(SPHERE,(0,0,1.2),box,(0,0,0))[0]==pytest.approx(0)
    assert gap(SPHERE,(0,0,1.7),box,(0,0,0))[0]==pytest.approx(.5)


@pytest.mark.parametrize('rid',IDS)
def test_all_recipes_seeded_and_bounded(rid):
    specs=recipe(rid)
    assert specs==recipe(rid)
    assert 1<=len(specs)<=12
    assert len({s['object_id'] for s in specs})==len(specs)
    assert Path('modules/blender/scenes/'+rid+'.py').is_file()
    for s in specs:
        assert s['keys'][0][0]==0 and s['keys'][-1][0]==1
        assert all(b[0]>a[0] for a,b in zip(s['keys'],s['keys'][1:]))
        assert all(math.isfinite(x) for x in position(s,.33))


def test_hero_matched_variant_preserves_identity_and_positive_gap():
    hit,miss=recipe(IDS[-1]),recipe(IDS[-1],variant='near_miss')
    assert [s['object_id'] for s in hit]==[s['object_id'] for s in miss]
    assert gap(hit[0],position(hit[0],.5),hit[1],position(hit[1],.5))[0]==pytest.approx(0)
    assert gap(miss[0],position(miss[0],.5),miss[1],position(miss[1],.5))[0]>0


def test_seed_changes_timing_and_unsupported_variant_is_explicit():
    assert recipe(IDS[-1],seed=41)[0]['keys']!=recipe(IDS[-1],seed=42)[0]['keys']
    with pytest.raises(ValueError,match='matched variants'):
        recipe(IDS[0],variant='near_miss')


def test_sampled_box_near_miss_cannot_hide_tunnelling():
    box={'shape':'box','half':(.5,.5,.5)}
    _,events=pair_timeline(SPHERE,box,[(0,(-10,0,0),(0,0,0)),(1,(5,0,0),(0,0,0)),(2,(10,0,0),(0,0,0))])
    assert not any(e['event_type']=='near_miss' for e in events)
