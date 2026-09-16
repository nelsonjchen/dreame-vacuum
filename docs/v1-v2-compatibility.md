# V1 / V2 compatibility research

Checked 2026-09-16 against upstream `master` (`ae8422f`, v1.0.11)
and `dev` (`3720223`, v2.0.0b25).

V2 retains the older integration's connection families. Its config flow offers
Xiaomi Home, Dreamehome, Movahome, Trouver, and manual local connection without
maps. The Mi Home protocol and local miio transport remain in the code. Existing
entries without an account type default to Mi Home in the coordinator and
reauth flow. Both versions use the `dreame_vacuum` integration domain, so v2
replaces v1; they are not separate integrations to install side by side.

A programmatic comparison of the two v1 model lists (`DREAME_MODELS` and
`MIJIA_MODELS`) against v2's decoded `DreameVacuumFlowHandler.load_devices()`
table found 59 v1 identifiers, 705 v2 identifiers, and 58 shared v1 identifiers.
The only missing v1 identifier is `dreame.vacuum.r2215o`, identified as L10s Pro
in v1's README. V2 includes `dreame.vacuum.r2216o` as L10s Pro, but that is a
different identifier; no equivalence or safe alias was established. This is a
static allowlist comparison, not validation of 58 devices on hardware.

V2 is not completely compatible with v1 automations. Published breaking changes
include removal of `set_dnd`, replacement of DND hour/minute numbers with time
entities, changes to customized cleaning arguments, conditional removal of the
vacuum entity's fan-speed support, and replacement of separate start/stop drying
buttons with a toggle button. Upgrading may require dashboard and automation
changes even when the same vacuum and account are supported.

The HA integration version does not determine which vendor phone app a robot
can join. V2 can integrate devices from different supported account types into
one Home Assistant installation. It does not transfer robots/accounts between
Xiaomi Home and Dreamehome or make every older robot compatible with Dreamehome.
The maintainer documents that local API availability depends on the robot's
cloud registration; Dreamehome registration can disable local control. App
migration or cloudless operation must be verified per model/firmware.

Sources:

- [V1 config flow](https://github.com/Tasshack/dreame-vacuum/blob/ae8422f/custom_components/dreame_vacuum/config_flow.py)
- [V2 config flow](https://github.com/Tasshack/dreame-vacuum/blob/3720223/custom_components/dreame_vacuum/config_flow.py)
- [V2 protocols](https://github.com/Tasshack/dreame-vacuum/blob/3720223/custom_components/dreame_vacuum/dreame/protocol.py)
- [V2 release notes / breaking changes](https://github.com/Tasshack/dreame-vacuum/releases/tag/v2.0.0b25)
- [Dreamehome account history](https://github.com/Tasshack/dreame-vacuum/discussions/109)
- [Maintainer explanation of local/cloud restrictions](https://github.com/Tasshack/dreame-vacuum/discussions/323)

For this fork, one maintained `main` branch is sufficient. Historical v1 commits
remain in Git history and the upstream remote. There is no evidence that we need
a separate v1 release line for the L50 Ultra.
