# How the Webex room-booking solution works today

Baseline for the self-hosted analysis: what the cloud solution actually does,
and which component owns which responsibility.

## 1. The Workspace is the unit of a room

A **Workspace** in Control Hub is the management object representing a physical
room. Devices are attached to it: a RoomOS codec (Room Kit / Room Bar / Board /
Desk), a Room Navigator, displays.

Control Hub distinguishes two ways a Navigator relates to a Workspace, and the
difference matters a lot for self-hosting:

- **Paired / companion Navigator** — cabled or network-paired to a codec. It
  has **no independent xAPI identity at all**. It is a remote screen for the
  codec; everything (config, status, bookings, UI) lives on the codec, and you
  address the panel specifically via `Target` / `Origin` / `PeripheralId`
  parameters on UI Extension commands (`Target: Controller|OSD|RoomScheduler`).
- **Standalone Navigator** — no codec, registered to Control Hub as its own
  device, running the native Room Scheduler panel with the LED strip
  (green = available, red = in use, yellow = booked but unoccupied / starting).

> Cisco's own note on standalone panels: *"The room booking app on a standalone
> device provides the same experience and functionality as a paired Room
> Navigator, **except for the sensor data and people count**."*

That sentence is the crux of the whole design. **The sensors live on the
codec**, not the panel. The "two devices connected in the Webex cloud" model
the project started from is really: both devices belong to the same Workspace,
and the cloud joins the codec's sensor telemetry to the panel's booking UI
through that shared Workspace identity.

## 2. Hybrid Calendar Service

The Hybrid Calendar is a **cloud service**, and its deployment shape depends
entirely on the calendar back end:

| Back end | Connector required | Mechanism |
|---|---|---|
| Exchange Online / Microsoft 365 | **None** — direct cloud-to-cloud | Webex subscribes to mailbox changes over **Microsoft Graph** |
| Exchange on-premises | **Expressway-C** registered to Webex as a Calendar Connector | Expressway-C talks to Exchange, relays to Webex |
| Google Workspace | None | Same keyword mechanics as M365 |

No other back end is supported. A self-hosted CalDAV/iCal server cannot be
plugged into the official Hybrid Calendar — which is precisely the gap this
project exists to fill.

For Microsoft 365, consent is granted to a multi-tenant Entra app with
*read/write calendars in all mailboxes*, *read/write all user mailbox
settings*, *read domains* and *read directory RBAC settings*. Worth noting when
comparing privacy posture: that is tenant-wide calendar write access granted to
a third party, where a self-hosted equivalent can be scoped to room mailboxes
only (see [calendar-backends.md](calendar-backends.md)).

What it reads and writes: meeting location/body (to find or inject the join
URI), title, start/end, invitee list, and the body for the agenda. Data is held
as a rolling window of **7 days past to 31 days future**, encrypted in the
Webex cloud.

The `@webex` / `@meet` keywords in the *location* field are the trigger: Webex
rewrites the invite with real join details, and pushes booking records to the
Workspace's devices, which is what produces **One Button To Push**.

One load-bearing dependency that is easy to miss: the **room resource mailbox
must auto-accept meeting requests**. If the room hasn't accepted the invite,
there's no booking on the room's calendar, so there's no OBTP — regardless of
calendar back end.

## 3. Occupancy sensing

All on the codec:

| xAPI path | Meaning |
|---|---|
| `xStatus RoomAnalytics PeopleCount Current` | Head count (camera-based head detection) |
| `xStatus RoomAnalytics PeoplePresence` | Boolean: anyone detected |
| `xStatus RoomAnalytics RoomInUse` | Composite "room is being used" signal |
| `xStatus RoomAnalytics AmbientNoise Level A` | dBA |

Key configuration:

- `xConfiguration RoomAnalytics PeopleCountOutOfCall` — **Off by default**.
  Must be `On` for occupancy detection outside a call, which is exactly the
  state a room-release feature cares about. On **Codec EQ / Codec Pro this
  requires a Quad Camera**. People count is never active in networked standby,
  and such devices won't enter networked standby until the count reaches 0.
- `xConfiguration RoomAnalytics PeoplePresenceDetector` — master toggle, with
  separate `PeoplePresence Input Ultrasound` and `Input HeadDetector`
  sub-toggles so camera-based detection can be disabled independently from
  ultrasound (a useful privacy lever).

Cisco does not publish accuracy, refresh interval or false-negative rates for
people counting. Treat it as something to characterise in a pilot room.

## 4. Room release — the Check-in / Check-out feature

This is what the project description called "release a room booking if
unoccupied". It is device-level, and the configuration is readable and
settable over the local xAPI:

```
xConfiguration Bookings CheckIn Enabled: <True/False>                    (default False)
xConfiguration Bookings CheckIn WindowDuration: <5,10,15,20,30,60>       (default 10 min)
xConfiguration Bookings AllowDecline: <All/InsideOnly/None>              (default All)
```

Behaviour, as documented:

1. A check-in button appears on the in-room and outside-room panels **5 minutes
   before** the booking starts.
2. The user has `WindowDuration` (default 10) minutes from the booking start to
   check in.
3. **Automatic** check-in fires on any of: an ad-hoc booking, joining a call,
   starting a share (wired or wireless), or **people count ≥ 1 sustained for
   one continuous minute**.
4. 30 seconds before the window closes, a 30-second countdown release alert is
   shown on the panel.
5. If nobody checks in, the booking is **released** and *"a notification is sent
   to the host to inform them about the canceled booking."*

Note what this is and isn't: it is a **check-in** model with occupancy as one
automatic trigger, not a continuous "room went empty mid-meeting, release it"
model. The commonly described "release after 15 minutes of no occupancy" is
this window expiring without a check-in.

Also note the honest gap: Cisco documents the user-visible outcome (booking
removed, organizer emailed) but not the exact Exchange-side protocol action
(decline vs. cancel vs. delete-occurrence). That ambiguity resurfaces as a real
design decision in the self-hosted version — see
[calendar-backends.md](calendar-backends.md) §"Releasing a booking".

## Sources

- [Workspaces in Control Hub](https://help.webex.com/en-us/article/noolw6w/Workspaces-in-Control-Hub)
- [Set up a Room Navigator in stand-alone mode](https://help.webex.com/en-us/article/iq6aw6/)
- [Set up Room Navigator as a room booking device](https://help.webex.com/en-us/article/55ypt4/Set-up-Room-Navigator-as-a-room-booking-device)
- [Hybrid Calendar with Microsoft 365 integration reference](https://help.webex.com/en-us/article/niqovwv/)
- [Deployment guide for Hybrid Calendar](https://help.webex.com/en-us/article/n6cwujdb/Deployment-guide-for-Hybrid-Calendar)
- [Hybrid Calendar Service for Google](https://help.webex.com/en-us/article/m2az0i/Hybrid-Calendar-Service-for-Google)
- [OBTP for Cloud-Registered Devices](https://help.webex.com/en-us/article/y5stdw/OBTP-for-Cloud-Registered-Devices)
- [cisco-ce/roomos.cisco.com](https://github.com/cisco-ce/roomos.cisco.com) — the xAPI schema and TechDocs source behind roomos.cisco.com
