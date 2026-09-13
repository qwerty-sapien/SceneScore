"""Fault controls for the mechanics/replay boundary, separate from physics tests."""
import copy

import pytest

from tools.direction_animations import check_packet


@pytest.fixture
def packet():
    pose = dict(position_m=[0, 0, 1], quaternion_xyzw=[0, 0, 0, 1],
                scale=[1, 1, 1], velocity_m_s=[0, 0, 0])
    return dict(duration_s=30, hz=240, actors=[dict(id='ball', shape='sphere', radius_m=.2)],
                geometry=[], states=[dict(tick=i, time_s=i/240, objects={'ball': copy.deepcopy(pose)})
                                     for i in range(7201)])


def test_valid_packet_and_no_rigid_shrinking(packet):
    assert check_packet(packet)['status'] == 'PASSED'
    packet['states'][701]['objects']['ball']['scale'] = [.999, 1, 1]
    with pytest.raises(AssertionError, match='changes rigid size'):
        check_packet(packet)


def test_retiming_rejected(packet):
    packet['states'][701]['time_s'] += 1/240
    with pytest.raises(AssertionError):
        check_packet(packet)


def test_nonfinite_motion_rejected(packet):
    packet['states'][701]['objects']['ball']['position_m'][0] = float('nan')
    with pytest.raises(ValueError):
        check_packet(packet)


def test_only_explicit_elastic_geometry_can_change_extent(packet):
    packet['actors'][0].update(id='spring', shape='coil', deformable=True)
    for sample in packet['states']:
        sample['objects']['spring'] = sample['objects'].pop('ball')
    packet['states'][701]['objects']['spring']['scale'] = [.9, 1, 1]
    assert check_packet(packet)['status'] == 'PASSED'
