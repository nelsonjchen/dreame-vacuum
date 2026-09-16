"""Room-order payloads must follow the selected map's protocol version."""
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock
import pytest
from custom_components.dreame_vacuum.dreame.device import DreameVacuumDevice, DreameVacuumDeviceStatus


@pytest.mark.parametrize('map_version,capability,expected', [(1, True, False), (2, False, True), (None, False, False), (None, True, True)])
def test_cleaning_sequence_protocol_is_boolean(monkeypatch, map_version, capability, expected):
    selected = SimpleNamespace(version=map_version) if map_version is not None else None
    monkeypatch.setattr(DreameVacuumDeviceStatus, 'selected_map', PropertyMock(return_value=selected))
    status = object.__new__(DreameVacuumDeviceStatus)
    status._device = SimpleNamespace(capability=SimpleNamespace(cleaning_sequence_v2=capability))
    assert status.cleaning_sequence_v2 is expected


@pytest.mark.parametrize('map_version,expected', [(1, {'cleanOrder': [7, 2]}), (2, {'cleanareaorder': [{'7': 1}, {'2': 2}]})])
def test_room_order_payload_uses_room_ids(monkeypatch, map_version, expected):
    monkeypatch.setattr(DreameVacuumDeviceStatus, 'selected_map', PropertyMock(return_value=SimpleNamespace(version=map_version)))
    monkeypatch.setattr(DreameVacuumDeviceStatus, 'has_temporary_map', PropertyMock(return_value=False))
    status = object.__new__(DreameVacuumDeviceStatus)
    status._device = SimpleNamespace(capability=SimpleNamespace(cleaning_sequence_v2=True))
    device = SimpleNamespace(status=status, _map_manager=SimpleNamespace(editor=SimpleNamespace(set_segment_order=Mock(return_value=[7, 2]))), update_map_data_async=Mock())
    DreameVacuumDevice.set_segment_order(device, 7, 1)
    device.update_map_data_async.assert_called_once_with(expected)
