# Stand-alone Room Navigator: what zero-cloud actually allows

**Status: settled.** This document records the decisive constraint for this
project, verified against Cisco's own primary sources, plus one empirical
finding from our own hardware.

## The decision

The deployment must be **zero-cloud**: no Control Hub, no Webex registration,
nothing. That places every Room Navigator in the **customer managed** bucket —
and that bucket does not get Cisco's native room booking UI.

## The three settings that define a Navigator

| Setting | Values | Our choice |
|---|---|---|
| `xCommand Provisioning SetType` | `PairedToCodec` / `Standalone` | `Standalone` |
| `xCommand SystemUnit SetTouchPanelMode` | `Controller` / `Scheduler` / `PersistentWebApp` | `PersistentWebApp` |
| `xConfiguration Provisioning Mode` | `Off` / `Auto` / `Webex` | **`Off`** — "customer managed" |

Note the Navigator's `Provisioning Mode` valuespace: `Off`, `Auto`, `Webex`.
There is **no CUCM, TMS, VCS or Edge option**. A stand-alone Navigator has
exactly two possible states — unregistered, or registered to Webex. There is no
on-premises-managed middle ground.

## What `Provisioning Mode: Off` excludes

From the *Cisco Room Navigator (stand-alone) API Reference Guide*, D15512.02,
RoomOS 11.9. Each of these carries the literal note **"Doesn't apply for a
customer managed Room Navigator"**:

```
xCommand Bookings Put            xStatus Bookings Availability Status
xCommand Bookings Book           xStatus Bookings Availability TimeStamp
xCommand Bookings Delete         xStatus Bookings Current Id
xCommand Bookings Get            xConfiguration RoomScheduler Enabled
xCommand Bookings List           xCommand Webex Registration Start
xCommand Bookings NotificationSnooze   xCommand Webex Registration Cancel
xCommand Bookings Respond        xStatus Webex Status
```

The Bookings family and the Webex registration commands are excluded by the
same rule. That is the tell: **customer managed ⟺ not Webex registered ⟺ no
booking APIs.** `RoomScheduler Enabled` reinforces it — the feature *"requires
the room to be set up with a calendar service that allows booking"*, and the
only calendar service a stand-alone Navigator can have is Webex's.

The one Bookings command **not** excluded is `xCommand Bookings Clear`.

## Resolving the apparent contradiction

Two Cisco sources looked like they disagreed. They don't — they describe
different sub-modes:

- The **RoomOS 11.9.2.4 release note** ("Standalone Room Navigator for
  on-premises management") says stand-alone *"is only supported with Persistent
  Web App mode"*. That describes the **customer managed** path. Still accurate.
- The **help.webex.com article** describing a stand-alone Navigator doing room
  booking *"without the Webex Hybrid Calendar"* states at its own top line that
  it covers **Webex-registered** Navigators. "Without Hybrid Calendar" removes
  the Exchange sync requirement, **not** the cloud registration requirement.

Both are true. They are non-overlapping deployment paths, and zero-cloud lands
us firmly in the first one.

## What customer managed *does* give us

This is why the concept still works:

| Capability | Note |
|---|---|
| **Persistent Web App** | Full-screen, undismissable, our own UI. Cisco's prescribed path for this mode |
| **Local xAPI** | WebSocket, HTTP `/putxml`, SSH — full access, local admin user |
| **`UserInterface LedControl Mode: Manual`** | **Not excluded.** Explicitly part of Cisco's own customer-managed setup walkthrough |
| **`xCommand UserInterface LedControl Color Set`** | `Green` / `Yellow` / `Red` / `Off` — we drive the strip ourselves |
| **Panel environmental sensors** | `RoomAnalytics AmbientTemperature`, `RelativeHumidity` |
| **Web app ↔ xAPI binding** | `Security Xapi WebSocket ApiKey Allowed: True` plus `WebEngine Features Xapi Peripherals AllowedHosts Hosts` |

Cisco describes LED Auto mode as *"green: room available, red: room in use"*.
In Manual mode we reproduce exactly those semantics from our own state.

## The Navigator has no occupancy sensing

The stand-alone guide's RoomAnalytics section lists **only**
`AmbientTemperature` and `RelativeHumidity`. There is no `PeopleCount`,
`PeoplePresence` or `RoomInUse` on the panel itself. Cisco's help content says
the same thing from the other direction: a stand-alone panel has the same
functionality as a paired one *"except for the sensor data and people count"*.

**Therefore occupancy must come from a separate in-room RoomOS video device**,
read over its own local xAPI, and correlated by our broker. There is no native
device-to-device link between a panel and a codec outside the Webex Workspace
association.

## Empirically confirmed

- `xCommand Bookings *` **works over the local API on a RoomOS video codec.**
  Confirmed on our own hardware. This does not contradict the above — the codec
  and the Navigator are different devices with different API surfaces.
- `xCommand Bookings *` **does not work from a macro.** Confirmed on our own
  hardware. Consistent with the schema: `Bookings Put` is `role: [Admin]` and
  the macro runtime does not carry Admin. All booking writes must therefore
  come from an external broker over WebSocket or HTTP, which is the right
  design anyway.

## The one open question worth a lab test

The stand-alone guide is **D15512.02, dated April 2024, RoomOS 11.9** — and no
newer revision exists. Confirmed by exhaustive search of Cisco's documentation
directory and Wayback CDX: only two revisions have ever been published (11.3
and 11.9), and the 11.9 file has been byte-identical for at least 16 months,
despite RoomOS 11.20, 11.32 and the entire RoomOS 26 line shipping since.

Meanwhile the **general** multi-product xAPI schema (26.9.1, Sept 2026) tags
`Bookings AdhocBooking Enabled`, the full Bookings family and
`UserInterface RoomScheduler Mode` for the Navigator's product code **with no
customer-managed caveat in their text**.

So either:

1. the general schema is simply less specific and the restriction still
   applies — most likely, given the weight of the specific evidence; or
2. Cisco quietly lifted the restriction after April 2024 and never updated the
   dedicated guide.

**This cannot be resolved from documentation.** The test is cheap: factory
reset a Navigator, choose *Set up as standalone → Customer managed*, then try

```
xCommand SystemUnit SetTouchPanelMode Mode: Scheduler
xCommand Bookings Put            (and Bookings Book)
```

and observe whether the commands return `OK` and whether the Scheduler screen
actually populates. If it works, the native Cisco UI comes back on the table
and the Persistent Web App becomes optional rather than required.

Until then, **build for Persistent Web App.**

## Sources

- Cisco Room Navigator (stand-alone) API Reference Guide, D15512.02, RoomOS 11.9 —
  [PDF](https://www.cisco.com/c/dam/en/us/td/docs/telepresence/endpoint/room_navigator-stand-alone/api/stand-alone-room-navigator-api-guide-roomos119.pdf)
- [RoomOS 11 release notes](https://github.com/cisco-ce/roomos.cisco.com/blob/master/doc/WhatsNew/ReleaseNotesRoomOS_11.md) — §11.9.2.4
- [Set up a Room Navigator in stand-alone mode](https://help.webex.com/en-us/article/iq6aw6/)
- [cisco-ce/roomos.cisco.com](https://github.com/cisco-ce/roomos.cisco.com) — versioned xAPI schema
