# Navigator On Prem

Feasibility study and (eventually) a self-hosted replacement for the **Webex
Hybrid Calendar**, driving Cisco **RoomOS** video endpoints and **Room
Navigator** booking panels from your own infrastructure instead of the Webex
cloud.

Goal: keep the Cisco hardware and its native booking UI, but move the
calendar brain on-premises — talking directly to Microsoft Graph, Exchange
on-prem, Google Workspace or CalDAV.

## Verdict up front

**Yes, this is buildable, and Cisco explicitly built the APIs for it.**

RoomOS 11.9.2.4 (Nov 2023) shipped a feature literally titled *"Support for
custom Cisco Scheduler setups without need for Webex Calendar"*, adding
`xConfiguration Bookings AdhocBooking Enabled` plus `xCommand Bookings
Book/Edit/Delete/Extend/CheckIn/CheckOut`. Combined with the long-standing
`xCommand Bookings Put` (bulk calendar injection, the OBTP path) and
`xCommand HttpFeedback Register` (webhook push of sensor + booking events),
every piece needed is a documented, local, non-cloud API.

Three caveats decide the shape of the solution — read them before planning
hardware:

| # | Caveat | Consequence |
|---|---|---|
| 1 | A **standalone** (codec-less) Navigator with **zero cloud** is documented as *Persistent Web App only* — you don't get Cisco's native scheduler UI | Either pair the Navigator to a codec (native UI, fully local) or build your own booking web app for standalone panels |
| 2 | Cisco's **"Permitted Commercial Use for Scheduled Meeting Join Experience"** clause covers `Bookings Put` and equivalents | Internal use is explicitly permitted. Productising/reselling this needs written permission from Cisco |
| 3 | A room mailbox can only **decline its own copy** of a meeting; only the organizer can truly cancel it | Sensor-driven "release" leaves a ghost on the organizer's calendar unless *your* service is the organizer of record |

Full reasoning: [docs/self-hosted-feasibility.md](docs/self-hosted-feasibility.md).

## How Webex does it today (short version)

```
Exchange Online room mailbox
        │  Microsoft Graph (cloud-to-cloud, no on-prem connector)
        ▼
Webex Hybrid Calendar Service ──── rolling window: -7d … +31d
        │  Webex cloud device channel
        ▼
Control Hub Workspace  ─┬─ RoomOS codec      ← people count / presence sensors live HERE
                        └─ Room Navigator    ← booking panel + LED strip
```

- A **Workspace** in Control Hub is the room object; the codec and the panel
  are both attached to it. That association — not a device-to-device link — is
  what ties "the panel on the wall" to "the camera that can see the room".
- The **Hybrid Calendar** subscribes to the room resource mailbox over Graph,
  rewrites `@webex` / `@meet` keywords into real join details, and pushes the
  resulting bookings down to the device, producing One Button To Push.
- **Occupancy** comes from the codec (`RoomAnalytics PeopleCount`,
  `PeoplePresence`, `RoomInUse`) — a standalone panel has no sensors of its own.
- **Room release** is the Check-in/Check-out feature: a check-in button appears
  5 minutes before start, the user has `Bookings CheckIn WindowDuration`
  (default 10 min) to check in, and *people count ≥ 1 for one continuous
  minute* counts as an automatic check-in. Miss the window and the booking is
  released and the organizer is emailed.

Detail and sources: [docs/how-webex-works-today.md](docs/how-webex-works-today.md).

## Proposed self-hosted architecture

```
                   ┌───────────────────────────────────────────┐
  RoomOS codec ───▶│                                           │
  (sensors,        │          booking broker (this repo)       │
   bookings,       │                                           │
   UI events)      │  • occupancy state machine                │
      ▲            │  • booking reconciler (room ⇄ calendar)   │
      │            │  • calendar driver interface              │
      └────────────│                                           │
   Bookings Put/   └──────────────────┬────────────────────────┘
   Book/Delete                        │
                       ┌──────────────┼───────────────┬──────────────┐
                       ▼              ▼               ▼              ▼
                  MS Graph        EWS (on-prem)   Google Cal      CalDAV
                  (Exch Online)                   (Workspace)   (Nextcloud…)
```

The broker owns one reconciliation loop per room: pull the authoritative
calendar view, push it to the device with `Bookings Put`, subscribe to device
events (`Bookings BookingRequested`, `RoomAnalytics PeopleCount`), and write
user-initiated changes back to the calendar.

## Status

Analysis only — **no code yet**. Nothing here has been validated against real
hardware; see the open questions at the end of the feasibility doc for the
items that need a lab endpoint to settle.

## Documents

| Document | Contents |
|---|---|
| [docs/how-webex-works-today.md](docs/how-webex-works-today.md) | The Webex/Control Hub/Hybrid Calendar architecture as it exists now |
| [docs/self-hosted-feasibility.md](docs/self-hosted-feasibility.md) | Device-side API surface, what's possible, gaps, risks, phasing |
| [docs/calendar-backends.md](docs/calendar-backends.md) | Graph / EWS / Google / CalDAV integration detail and pitfalls |
