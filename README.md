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
| 1 | **Settled:** zero-cloud means `Provisioning Mode: Off` ("customer managed"), and Cisco documents the entire `Bookings` family plus `RoomScheduler Enabled` as not applicable in that mode | Standalone panels run a **Persistent Web App** — our own UI — with the LED strip driven manually. See [docs/standalone-navigator-constraints.md](docs/standalone-navigator-constraints.md) |
| 2 | Cisco's **"Permitted Commercial Use for Scheduled Meeting Join Experience"** clause covers `Bookings Put` and equivalents | Internal use is explicitly permitted. Productising/reselling this needs written permission from Cisco |
| 3 | A room mailbox can only **decline its own copy** of a meeting; only the organizer can truly cancel it | Sensor-driven "release" leaves a ghost on the organizer's calendar unless *your* service is the organizer of record |

Two findings confirmed on our own hardware:

- `xCommand Bookings *` **works over the local API on a RoomOS video codec**.
- `xCommand Bookings *` **does not work from a macro** — consistent with
  `Bookings Put` being `role: [Admin]`. All booking writes come from an
  external broker, which is the right design anyway.

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

Two independent devices per room, joined by the broker — replacing the Webex
Workspace association that used to connect them.

```
  MEETING ROOM                                   CALENDAR
  ┌──────────────────────────┐
  │ Room Navigator           │   UI + LED
  │ standalone · outside room│──────────┐
  │ Provisioning Mode: Off   │          │
  │ PersistentWebApp         │          ▼
  └──────────────────────────┘    ┌───────────┐      ┌──────────────────┐
  ┌──────────────────────────┐    │  broker   │─────▶│ Exchange Online  │
  │ RoomOS video device      │    │           │Graph │ EWS · Google     │
  │ people count / presence  │───▶│           │      │ CalDAV           │
  └──────────────────────────┘    └───────────┘      └──────────────────┘
                          sensors
```

The broker owns one reconciliation loop per room: pull the authoritative
calendar view, render it in the panel web app, drive the LED strip with
`UserInterface LedControl Color Set`, subscribe to occupancy on the codec, and
write user-initiated changes back to the calendar.

## Concept deck

[`concept/Self-hosted-room-booking-concept.pptx`](concept/) — 17 slides
covering the device configuration, panel UI mockups, booking and release
flows, the Graph integration and the management UI. Mockup sources are in
`concept/src/` and regenerate with Playwright + python-pptx.

## Status

Analysis only — **no code yet**. Nothing here has been validated against real
hardware; see the open questions at the end of the feasibility doc for the
items that need a lab endpoint to settle.

## Documents

| Document | Contents |
|---|---|
| [docs/how-webex-works-today.md](docs/how-webex-works-today.md) | The Webex/Control Hub/Hybrid Calendar architecture as it exists now |
| [docs/standalone-navigator-constraints.md](docs/standalone-navigator-constraints.md) | **Settled constraint:** what customer-managed mode allows, and the one open lab test |
| [docs/self-hosted-feasibility.md](docs/self-hosted-feasibility.md) | Device-side API surface, what's possible, gaps, risks, phasing |
| [docs/calendar-backends.md](docs/calendar-backends.md) | Graph / EWS / Google / CalDAV integration detail and pitfalls |
