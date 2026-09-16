# L50 Ultra plugin comparison — 2026-09-16

## Verified device and artifacts

Authorized US Dreamehome account metadata identifies the owner's vacuum as
`dreame.vacuum.r9493h`, L50 Ultra, firmware `4.3.9_6000`.
No inference from retail branding or guessed model aliases was used.

The model's React Native plugin metadata returns model revision 30, common
plugin version 2236, and resource package version 19. The downloaded project
identifies itself as `dreame.vacuum.common`, versionCode 2236, Android.
The plugin archive SHA-256 is
`227374ac37ef4ec83b4224339008d4164a651b1ab6e5011754412edada29566c`;
its inner `index.android.bundle` matches metadata MD5
`59304e51e4846dffb0734cccc5cc5521`. The MD5 is for the bundle, not its ZIP.
The resources ZIP SHA-256 is
`746809db04edb263ca18714ceee92a067c20599f3420209793d2f139aca72c2f`;
its ZIP matches metadata MD5 `c062521fc19ebe2c0c00137ef65ba2e2`.

Vendor code and authenticated metadata remain ignored in the adjacent local
`dreamehome-re` workspace. They are not distributed with this integration.
The independent tests contain only protocol observations, not vendor source.

## Compared behavior

The resource configuration enables the following features. Common-plugin
`GeneralProtocol.initProps` (bundle lines 177841–177907) assigns their service
and property IDs. These match this integration:

| Setting | Service/property | Result |
| --- | --- | --- |
| Carpets first | 28/2 | Already supported |
| Wash-water temperature | 28/8 | Already supported |
| DND resume/empty/volume | 28/14, 28/15, 28/16 | Already supported |
| Dynamic obstacle cleaning | 28/18 | Already supported |
| Smart mop washing | 28/22 | Already supported |
| Silent drying | 28/27 | Already supported |
| Hair compression | 28/28 | Already supported |
| Side brush on carpets | 28/29 | Already supported |
| Obstacle crossing | 28/38 | Already supported |
| Power saving | 28/63 | Already supported |

The app uses a five-hour silent drying duration (Const line 1219 and
formatRemainingTime lines 241099–241116), matching the integration default.
Model capability tests use the verified firmware build 6000. Missing live
property responses are mocked; these tests do not prove hardware behavior.

## Fixed room-order bug

The app's commitCleanOrder (lines 285874–285914) distinguishes legacy `cleanOrder`
arrays from newer `cleanareaorder` arrays of room-ID/order objects. A two-room
new-format example is `{"cleanareaorder":[{"7":1},{"2":2}]}`.

The integration already encodes both formats, but `cleaning_sequence_v2` lacked
its property decorator. Callers consequently tested a bound method, which is
always true, instead of the selected map/capability boolean. This forced the
new format even when the existing selection logic required the legacy format.
Adding the decorator restores that logic without inventing a new model rule.
The modern L50 path remains covered alongside legacy-map and no-map fallbacks.
This is a reproduced code defect, not a claim of a hardware failure observed
on the owner's vacuum. Five of six new regression cases failed before the fix.

The earlier key-table bounds fix remains covered separately. No additional
feature was added merely because its name appeared in the shared plugin:
shared code includes other models and internal diagnostic controls.

## Owner hardware validation

1. Install this fork's main and confirm diagnostics identify r9493h/build 6000.
2. Compare the settings above and drying time with Dreamehome's current values.
3. With the vacuum idle, change room order using two actual room IDs; confirm
   the app displays the same order, then restore the original order.
4. Reload/unload the integration and verify reconnect and entity recovery.
5. Observe memory/thread counts over a longer normal-use period.

No device property write, cleaning command, firmware change, or hardware test
was performed here. Authenticated calls were login, account device metadata,
and plugin metadata/downloads. Full parity for every page of the shared app,
all firmware versions, and every other model is not established by this audit.
