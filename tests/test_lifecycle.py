"""Exercise real integration lifecycle code with Home Assistant and mocked I/O."""
import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState, current_entry
from homeassistant.helpers import frame
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

import custom_components.dreame_vacuum as integration
from custom_components.dreame_vacuum import coordinator as module
from custom_components.dreame_vacuum.const import DOMAIN
from custom_components.dreame_vacuum.dreame.device import DreameVacuumDevice


@pytest.fixture
async def environment(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    entry = Mock()
    entry.entry_id = 'l50-test'
    entry.state = ConfigEntryState.SETUP_IN_PROGRESS
    entry.data = {'name': 'L50 Ultra', 'host': '', 'token': ''}
    entry.options = {'version': module.VERSION}
    frame.async_setup(hass)
    entry_context = current_entry.set(entry)
    device = Mock()
    device.auth_failed = False
    device.disconnected = False
    device.status = None
    monkeypatch.setattr(module, 'DreameVacuumDevice', Mock(return_value=device))
    unsubscribe = Mock()
    monkeypatch.setattr(module, 'async_dispatcher_connect', Mock(return_value=unsubscribe))
    hass.config_entries = SimpleNamespace(
        async_forward_entry_setups=AsyncMock(),
        async_unload_platforms=AsyncMock(return_value=True),
        async_update_entry=Mock(),
    )
    coordinators = []
    def make():
        coordinator = module.DreameVacuumDataUpdateCoordinator(hass, entry=entry)
        coordinators.append(coordinator)
        return coordinator
    yield hass, entry, device, unsubscribe, make
    for coordinator in coordinators:
        await coordinator.async_shutdown()
    await hass.async_stop()
    current_entry.reset(entry_context)


@pytest.mark.parametrize('auth_failed', [False, True])
async def test_failed_update_cleans_resources(environment, auth_failed):
    hass, entry, device, unsubscribe, make = environment
    device.auth_failed = auth_failed
    device.update.side_effect = RuntimeError('cloud unreachable')
    coordinator = make()
    with pytest.raises(ConfigEntryAuthFailed if auth_failed else UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.device is None
    device.disconnect.assert_called_once()
    device.listen.assert_called_with(None)
    device.listen_error.assert_called_with(None)
    unsubscribe.assert_called_once()
    await coordinator.async_shutdown()
    device.disconnect.assert_called_once()


async def test_auth_failure_after_successful_update(environment):
    _, _, device, _, make = environment
    device.auth_failed = True
    coordinator = make()
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
    device.disconnect.assert_called_once()
    device.schedule_update.assert_not_called()


async def test_cancelled_executor_finishes_before_disconnect(environment):
    _, _, device, unsubscribe, make = environment
    started, release = threading.Event(), threading.Event()
    order = []
    def update():
        started.set()
        assert release.wait(5)
        order.append('update finished')
    device.update.side_effect = update
    device.disconnect.side_effect = lambda: order.append('disconnected')
    coordinator = make()
    task = asyncio.create_task(coordinator._async_update_data())
    try:
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        await asyncio.sleep(0)
        device.disconnect.assert_not_called()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert order == ['update finished', 'disconnected']
        unsubscribe.assert_called_once()
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_cleanup_error_preserves_original_failure(environment):
    _, _, device, unsubscribe, make = environment
    device.update.side_effect = RuntimeError('original discovery error')
    device.disconnect.side_effect = RuntimeError('cleanup error')
    coordinator = make()
    with pytest.raises(UpdateFailed, match='original discovery error'):
        await coordinator._async_update_data()
    unsubscribe.assert_called_once()


async def test_setup_failure_does_not_publish_coordinator(environment, monkeypatch):
    hass, entry, device, _, make = environment
    coordinator = make()
    device.update.side_effect = RuntimeError('cloud unreachable')
    monkeypatch.setattr(integration, 'DreameVacuumDataUpdateCoordinator', Mock(return_value=coordinator))
    with pytest.raises(ConfigEntryNotReady):
        await integration.async_setup_entry(hass, entry)
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
    device.disconnect.assert_called_once()


async def test_platform_setup_failure_cleans_resources(environment, monkeypatch):
    hass, entry, device, _, make = environment
    coordinator = make()
    monkeypatch.setattr(integration, 'DreameVacuumDataUpdateCoordinator', Mock(return_value=coordinator))
    hass.config_entries.async_forward_entry_setups.side_effect = RuntimeError('platform failure')
    with pytest.raises(RuntimeError, match='platform failure'):
        await integration.async_setup_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]
    device.disconnect.assert_called_once()


async def test_success_and_failed_then_successful_unload(environment, monkeypatch):
    hass, entry, device, unsubscribe, make = environment
    coordinator = make()
    monkeypatch.setattr(integration, 'DreameVacuumDataUpdateCoordinator', Mock(return_value=coordinator))
    assert await integration.async_setup_entry(hass, entry)
    assert hass.data[DOMAIN][entry.entry_id] is coordinator
    device.schedule_update.assert_called_once()
    device.disconnect.assert_not_called()
    hass.config_entries.async_unload_platforms.return_value = False
    assert not await integration.async_unload_entry(hass, entry)
    device.disconnect.assert_not_called()
    hass.config_entries.async_unload_platforms.return_value = True
    assert await integration.async_unload_entry(hass, entry)
    device.disconnect.assert_called_once()
    unsubscribe.assert_called_once()
    assert entry.entry_id not in hass.data[DOMAIN]
    # Queued callbacks from a worker must be harmless after shutdown.
    coordinator.async_set_updated_data()
    coordinator.async_set_update_error(RuntimeError('late error'))


def test_device_disconnect_cancels_all_timers_even_if_protocol_fails():
    device = object.__new__(DreameVacuumDevice)
    device.disconnected = False
    timers = [Mock(), Mock(), Mock()]
    device._update_timer, device._keep_alive_timer, device._callback_timer = timers
    device._protocol = Mock()
    device._protocol.disconnect.side_effect = RuntimeError('transport error')
    device._map_manager = Mock()
    with pytest.raises(RuntimeError, match='transport error'):
        device.disconnect()
    for timer in timers:
        timer.cancel.assert_called_once()
    device._map_manager.disconnect.assert_called_once()
    assert device.disconnected
    device.schedule_update(0)
    assert device._update_timer is None


async def test_second_cancellation_does_not_cancel_cleanup(environment):
    _, _, device, _, make = environment
    started, release = threading.Event(), threading.Event()
    def update():
        started.set()
        assert release.wait(5)
    device.update.side_effect = update
    coordinator = make()
    task = asyncio.create_task(coordinator._async_update_data())
    try:
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        while coordinator._shutdown_task is None:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not coordinator._shutdown_task.cancelled()
        release.set()
        await coordinator.async_shutdown()
        device.disconnect.assert_called_once()
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_disconnected_initial_update_is_not_success(environment):
    _, _, device, _, make = environment
    device.disconnected = True
    coordinator = make()
    with pytest.raises(UpdateFailed, match='disconnected'):
        await coordinator._async_update_data()
    device.disconnect.assert_called_once()


async def test_repeated_failures_stop_real_workers_and_timers(environment, monkeypatch):
    """100 setup attempts, real device/cloud teardown and threads, no network."""
    import gc
    import weakref
    from custom_components.dreame_vacuum.dreame.protocol import DreameVacuumDreameHomeCloudProtocol
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    hass, entry, _, _, _ = environment
    monkeypatch.setattr(module, 'async_dispatcher_connect', async_dispatcher_connect)
    unload_callbacks = []
    entry.async_on_unload = unload_callbacks.append
    workers = []
    references = []
    closed_sessions = []

    def make_device(*args, **kwargs):
        device = DreameVacuumDevice('L50', '', '')
        cloud = DreameVacuumDreameHomeCloudProtocol('fake', 'fake', country='us')
        session = Mock()
        cloud._session.close()
        cloud._session = session
        closed_sessions.append(session)
        device._protocol = cloud
        def fail():
            # The API queue consumer is real; transport activity is mocked.
            cloud._api_call = Mock(return_value=None)
            cloud._api_call_async(Mock(), '/mock')
            workers.append(cloud._thread)
            for attr in ('_update_timer', '_keep_alive_timer', '_callback_timer'):
                timer = threading.Timer(60, lambda: None)
                timer.daemon = True
                timer.start()
                setattr(device, attr, timer)
                workers.append(timer)
            raise RuntimeError('Unable to discover the device over cloud')
        device.update = fail
        references.append(weakref.ref(device))
        return device

    monkeypatch.setattr(module, 'DreameVacuumDevice', make_device)
    for _ in range(100):
        coordinator = module.DreameVacuumDataUpdateCoordinator(hass, entry=entry)
        references.append(weakref.ref(coordinator))
        try:
            await coordinator._async_update_data()
        except UpdateFailed:
            pass
        else:
            pytest.fail('Expected discovery failure')
        assert coordinator.device is None
        # HA runs and clears these callbacks after a failed setup attempt.
        for cleanup in unload_callbacks:
            await cleanup()
        unload_callbacks.clear()
        del cleanup
    for worker in workers:
        await asyncio.to_thread(worker.join, 2)
    assert all(not worker.is_alive() for worker in workers)
    for session in closed_sessions:
        session.close.assert_called_once()
    del coordinator
    await asyncio.sleep(0)
    gc.collect()
    assert all(ref() is None for ref in references)


def test_l50_ultra_is_in_bundled_supported_models():
    from custom_components.dreame_vacuum.config_flow import DreameVacuumFlowHandler
    flow = DreameVacuumFlowHandler()
    flow.load_devices()
    assert 'dreame.vacuum.r9493a' in flow.models
    assert 'dreame.vacuum.r9493h' in flow.models
