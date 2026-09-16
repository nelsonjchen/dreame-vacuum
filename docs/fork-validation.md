# L50 Ultra maintenance fork

This fork starts at Tasshack/dreame-vacuum `dev`, commit
`3720223`, upstream version `v2.0.0b25`. The maintained branch is `main`; `upstream/dev` is the source for upstream updates.
The first patch addresses setup/shutdown resource ownership. It has been tested
locally with Home Assistant 2026.8.3 and Python 3.14; HACS minimum version is
set to this tested baseline. No vacuum or cloud account
was used. It is not yet hardware validated.

## Basis and changes

The investigation and cleanup approach are based on
[BigKelLearns' PR #1774](https://github.com/Tasshack/dreame-vacuum/pull/1774),
commit `a5e8c6661d8f6be3e582c9c8d68a56b2641b6d79`, and
[issue #1762](https://github.com/Tasshack/dreame-vacuum/issues/1762).
The PR was used as a guide, not applied as a verified fix.

The current upstream snapshot already cleans up ordinary update exceptions.
Authentication failures can bypass that cleanup, and cancellation is not caught
by `except Exception`. This patch:

- Uses one idempotent coordinator shutdown path for setup errors, authentication
  failures, cancellation, platform setup failures, and successful unload.
- Removes update/error listeners and the notification dispatcher subscription.
- Preserves authentication failures for HA reauthentication and propagates
  cancellation rather than converting it into a retryable update error.
- Shields the executor update future. Cancellation cannot stop its thread;
  shutdown waits for the update to finish before disconnecting resources that
  the update might still create. A second cancellation cannot cancel cleanup.
- Runs disconnect in the executor so blocking transport shutdown does not run
  on HA's event loop. Logs disconnect errors without masking the setup error.
- Cancels the device's pending debounced callback timer, prevents scheduling a
  new device update after disconnect, and stops the map manager even if protocol
  disconnect raises.
- Passes the config entry explicitly to Home Assistant's coordinator and invokes
  its own shutdown implementation as part of cleanup.

Unlike the proposed upstream patch, cancellation handling accounts for the
executor still running, and normal unload shares the same cleanup code.
This is not a timer implementation rewrite or a complete protocol audit.

## Reproduce local checks

```sh
cd ~/code/dreame-vacuum
uv venv --python 3.14
uv pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
```

The suite imports real Home Assistant and integration modules. Device/network
responses are mocked. Network connections are prohibited by the test fixture.
It covers discovery and authentication failures, cancellation and repeated
cancellation, cleanup errors, successful setup, failed/successful unload,
platform setup failure, late callbacks, and disconnected initial updates.

The stress case performs 100 failed attempts with real Dreame cloud queue workers
and device timers: 400 threads/timers in total. It verifies that they terminate,
mock HTTP sessions close, and weak references to devices/coordinators clear after
garbage collection. This checks resource ownership; it is not an RSS benchmark
or a live MQTT/cloud soak test.

Selected regression tests were also run against unpatched upstream in a temporary
copy. The authentication cleanup and callback-timer cleanup tests failed there;
the ordinary discovery-error test passed, matching the inspected code.
The same cancellation-order and callback-timer tests were run against PR #1774's
actual head in a temporary copy. Both failed: it disconnects while the executor
update is still running and does not cancel the pending callback timer.
All 13 tests pass against this fork's patch on macOS and the GitHub Actions
Ubuntu runner. Home Assistant hassfest validation also passes.

## L50 model boundary

The bundled upstream table includes `dreame.vacuum.r9493a` and
`dreame.vacuum.r9493h` as L50 Ultra models; tests check both entries load.
The older L50 issue #1156 mentioned `dreame.vacuum.r2529a`, which this snapshot
does not include. The purchase receipt confirms the marketing model, not the
protocol identifier. Check the actual device's reported identifier during setup.
Do not add a guessed alias or force a different model's capability table.

## Install for user-led hardware validation

Do not run the inherited upstream installer: it downloads the unpatched upstream
release. For this first validation build, copy this checkout's
`custom_components/dreame_vacuum` directory into HA's `config/custom_components/`,
replacing the prior integration directory after taking a backup. Restart HA.
Avoid keeping two copies of the same `dreame_vacuum` integration installed.
There is no packaged fork release yet; use the recorded fork commit.

The manifest version remains the upstream version because this is a development
patch rather than a published release. Record the Git commit alongside it.

Hardware checks for the user:

1. Record HA version, vacuum firmware, account region, and actual model ID.
2. Verify Dreamehome login, entity discovery, maps, and room selection.
3. Verify start/pause/return-to-dock, room cleaning, mop wash/dry, and relevant
   dock states. Ensure map room IDs match the requested rooms.
4. Reload and restart several times; check duplicate entities, callbacks, and
   unexpected commands.
5. Make the device/cloud unreachable during setup and after successful setup;
   watch HA responsiveness, RSS, and **live** thread count over an extended run.
   Monotonically increasing thread names alone do not establish a leak.
6. Restore connectivity and verify recovery; test reauthentication as needed.

Limits: mocked responses do not prove real cloud discovery, MQTT reconnects,
firmware-specific capabilities, or every timer race correct. Shutdown must wait
for an in-flight synchronous update's network calls to return; if one hangs
indefinitely, Python cannot forcibly cancel that worker. Hardware validation and
an outage soak remain required before calling this deployment proven.

## Capability metadata index validation

The loader checked device key indexes against the capability table instead of
its separate key table. This could reject a valid key or allow an invalid index
to raise an unhelpful IndexError. The comparison now uses the key table.
Four offline regression cases cover a valid key above the capability-table bound
and negative/out-of-range key indexes. Three cases failed before the fix; all
17 tests pass after it. This is a general metadata-loader fix, not a claim of
an observed fault on Nelson's L50 or a new device capability.

See [the L50 plugin audit](l50-plugin-audit.md) for verified model provenance,
protocol comparisons, the room-order fix, and hardware validation steps.
