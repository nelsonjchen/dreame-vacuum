"""Capability metadata must validate indexes against the table being indexed."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.dreame_vacuum.dreame.types import DreameVacuumDeviceCapability


def capability():
    device = SimpleNamespace(
        info=SimpleNamespace(model='dreame.vacuum.test', version=1),
        get_property=Mock(return_value=None),
        _map_manager=None,
        status=SimpleNamespace(current_segments=None, selected_map=None, current_map=None),
    )
    return DreameVacuumDeviceCapability(device)


def test_key_index_is_independent_of_capability_count():
    subject = capability()
    subject.load([[[0, 'Test', 0, 1]], [[]], ['first', 'second'], {'test': 0}])
    assert subject.loaded
    assert subject.key == 'second'


@pytest.mark.parametrize('key_index', [-1, 1, 2])
def test_missing_key_has_explicit_error(key_index):
    subject = capability()
    with pytest.raises(Exception, match='Device key missing!'):
        subject.load([[[0, 'Test', 0, key_index]], [[], [], []], ['first'], {'test': 0}])
    assert not subject.loaded
