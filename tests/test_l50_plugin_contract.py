"""Independent expectations observed in official common plugin 2236/resource 19.

Source bundle SHA256 and extraction notes are in docs/l50-plugin-audit.md.
No vendor source, credentials, or network access are needed for these tests.
"""
import base64
import json
import zlib
from types import SimpleNamespace
from unittest.mock import Mock

from custom_components.dreame_vacuum.dreame.const import DEVICE_INFO
from custom_components.dreame_vacuum.dreame.types import (
    DreameVacuumDeviceCapability, DreameVacuumProperty, DreameVacuumPropertyMapping,
)


def test_l50_firmware_6000_capabilities_match_observed_app_features():
    device = SimpleNamespace(
        info=SimpleNamespace(model='dreame.vacuum.r9493h', version=6000),
        get_property=Mock(return_value=None), _map_manager=None,
        status=SimpleNamespace(current_segments=None, selected_map=None, current_map=None, fill_light=None),
    )
    capability = DreameVacuumDeviceCapability(device)
    capability.load(json.loads(zlib.decompress(base64.b64decode(DEVICE_INFO), 31)))
    for name in ('hair_compression', 'silent_drying', 'smart_mop_washing',
                 'water_temperature', 'clean_carpets_first', 'side_brush_carpet_rotate',
                 'obstacle_crossing', 'power_saving', 'cleaning_sequence_v2', 'curtains'):
        assert getattr(capability, name) is True, name
    assert capability.silent_drying_time == 5


def test_l50_settings_addresses_match_official_general_protocol():
    observed = {
        'CLEAN_CARPETS_FIRST': 2, 'WATER_TEMPERATURE': 8,
        'DND_DISABLE_RESUME_CLEANING': 14, 'DND_DISABLE_AUTO_EMPTY': 15,
        'DND_REDUCE_VOLUME': 16, 'DYNAMIC_OBSTACLE_CLEANING': 18,
        'SMART_MOP_WASHING': 22, 'SILENT_DRYING': 27, 'HAIR_COMPRESSION': 28,
        'SIDE_BRUSH_CARPET_ROTATE': 29, 'OBSTACLE_CROSSING': 38, 'POWER_SAVING': 63,
    }
    for name, property_id in observed.items():
        assert DreameVacuumPropertyMapping[DreameVacuumProperty[name]] == {'siid': 28, 'piid': property_id}, name
