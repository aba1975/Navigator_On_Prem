# Self-hosted feasibility analysis

Can the Webex cloud be removed from the room-booking path while keeping Cisco
RoomOS endpoints and Room Navigator panels? **Yes.** This document sets out the
exact API surface, what is verified vs. inferred, and where the real risks sit.

---

## 1. The decisive fact: local xAPI is not gated by cloud registration

Cisco's own integration-methods matrix classifies the transports like this:

| Method | On-prem / cloud | Latency | Access control | API access |
|---|---|---|---|---|
| Macros (JS on device) | **Both** | Instant | Local user | **Full** |
| JSXAPI / WebSocket | **Both** | Very low | Local user | **Full** |
| HTTP(S) `/getxml`, `/putxml` | **Both** | Low | Local user (Basic) | **Full** |
| SSH / RS-232 | **Both** | Low | Local user | **Full** |
| Cloud xAPI / Workspace Integrations | **Cloud only** | ~1 s | OAuth token | **Reduced** |

Only the cloud REST path is restricted. Every locally-reached transport is
documented as working on-prem *and* cloud-registered, with full API access.

Cisco also demonstrates that it **documents registration gating explicitly when
it exists**: `xCommand Bookings Respond` (accept/decline an invite) carries the
note *"applies to devices that are either registered to the Webex cloud service
or registered to an on-premises service and linked to Webex Edge for Devices."*
No such note appears on `Bookings Put`, `Book`, `Edit`, `Delete` or `List`.
Strong evidence, though not an explicit "works unregistered" sentence — flagged
as open question OQ-1 below.

> On cloud-registered devices, local access survives only if **"Disable local
> users and integrations"** is left unchecked during registration. Relevant if
> you migrate existing Control Hub devices rather than starting fresh.

---

## 2. Writing bookings to the device

Two complementary write paths, both verified against the live RoomOS 26.9.1
xAPI schema.

### 2a. `xCommand Bookings Put` — bulk calendar injection (the OBTP path)

Multiline command, JSON payload, **replaces the entire stored booking list**.
Role: `Admin` only.

```json
{
  "Bookings": [
    {
      "Id": "1",
      "Title": "Booking Title",
      "Number": "number@example.com",
      "Protocol": "WebRTC",
      "MeetingPlatform": "MicrosoftTeams",
      "Organizer": { "Name": "John Smith" },
      "Time": {
        "StartTime": "2024-06-04T08:40:42.300000000Z",
        "Duration": 60,
        "EndTimeBuffer": 50
      }
    }
  ]
}
```

Full field set: `Id, MeetingId, Agenda, Title, Privacy (Private/Public),
Protocol (SIP/H323/ISDN/IP/Spark/WebRTC/None), MeetingPlatform
(GoogleMeet/MicrosoftTeams/Zoom/Webex/Other/None), MetaInfo, Time{StartTime,
Duration, StartTimeBuffer, EndTimeBuffer}, Organizer{Name, Email, Id}, Number,
CallType, Encryption`. Required: `Id, Title, Number, Protocol, Organizer/Name,
Time/StartTime, Time/Duration`.

State-dependent: **unavailable when the device is in Microsoft Teams Rooms or
Zoom mode.** If any rooms run MTR, they are out of scope for this approach.

This is the direct successor to the old private `bookingsputxml` HTTP API that
Cisco TMS/TMSXE used — i.e. the same mechanism that has driven on-prem room
booking for a decade, still shipping.

### 2b. `Bookings Book / Edit / Delete / Extend / CheckIn / CheckOut / Clear`

Added in **RoomOS 11.9.2.4** under a release note titled *"Support for custom
Cisco Scheduler setups without need for Webex Calendar"*:

> *"We have added an option to enable ad-hoc bookings on a Room Device without
> having any integrations to a Webex Hybrid Calendar. This feature involves
> several new xConfigurations and xCommands for custom bookings."*

```
xConfiguration Bookings AdhocBooking Enabled          # enable ad-hoc booking
xConfiguration UserInterface RoomScheduler Mode       # full calendar vs. in-use/available only

xCommand Bookings Book BookingRequestUUID: 1 MeetingPlatform: Webex \
    Number: meeting@example.com OrganizerName: "Booker" Protocol: Spark \
    Title: "Webex Local Booking"
xCommand Bookings Edit MeetingId: 1 Title: "..." Number: "..." MeetingPlatform: MicrosoftTeams
```

Role `Admin, User` — less privileged than `Put`, and non-destructive
(incremental rather than full-list replace).

**This feature existing at all is the strongest signal in the whole analysis.**
Cisco anticipated exactly this use case and shipped first-class support for it.

### 2c. Read side and events

- `xCommand Bookings List [Days] [DayOffset] [Limit] [Offset] [ScheduleType: Current|Upcoming]`
- `xCommand Bookings Get [Id|MeetingId]`
- `xStatus Bookings Current Id`, `Bookings Availability Status`, `Bookings Availability TimeStamp`
- `xEvent Bookings` — `Start`, `End`, `Deleted`, `SyncRequired`,
  `BookingRequested`, `BookingCreated`, `BookingFailed`, `BookingMoved`,
  `EditRequested`, `EditFailed`, `ExtensionRequested`, `ExtensionFailed`

The event set is what makes the native UI usable against a custom backend: the
panel emits `BookingRequested` when a user taps "book this room", your broker
does the calendar write, then confirms with `Bookings Book`/`Put`. The
request/created/failed triad is designed for exactly that async round-trip.

---

## 3. Getting data out of the device

- **`xCommand HttpFeedback Register`** — device POSTs XML or JSON to your URL on
  change. Up to 15 XPath expressions per call, 50 total, across 4 feedback
  slots. **Avoid slot 3** (reserved by Cisco TMS). Role: `Admin`.
- **WebSocket / JSXAPI** — persistent outbound-friendly subscription, very low
  latency, the better default for a broker that holds state.
- **Macros** — on-device JavaScript (QuickJS since RoomOS 11.14) with
  `HttpClient Get/Post/Put/Patch/Delete` for outbound calls. Requires
  `HttpClient Mode: On`, plus `AllowHTTP` / `AllowInsecureHTTPS` for plain HTTP
  or self-signed certs. **Only one in-flight HTTP request per device** — a
  second before awaiting the first throws `"No available http connections"`.

> **Confirmed on our hardware: `xCommand Bookings *` does not work from a
> macro.** This is consistent with `Bookings Put` being `role: [Admin]`, which
> the macro runtime does not carry. Macros are therefore not an option for
> booking writes — use the external broker over WebSocket or HTTP.

Recommended split: WebSocket subscription from the broker for state, macros
only for UI glue that must survive broker downtime.

---

## 4. UI options

| Option | Native Cisco look | Needs cloud | Notes |
|---|---|---|---|
| Native Room Scheduler UI + local bookings | Yes | No (paired) | Best option; UI Extensions can **add** panels/buttons alongside it |
| UI Extensions (panels, action buttons, web apps) | Yes | No | Room Scheduler supports Panels/Action Buttons/Web Apps; **Web Widgets are not supported** in scheduler mode. Target with `Target: RoomScheduler` |
| Persistent Web App | No — your own design | No | Takes over the whole screen, cannot be dismissed by users. Configurable entirely from the local web interface. Embedded JSXAPI auto-connects to the paired codec |

UI Extensions **add to** the native scheduler, they don't replace it. Full
replacement means Persistent Web App.

---

## 5. Hardware topology — decided

The deployment must be zero-cloud, which settles this. See
[standalone-navigator-constraints.md](standalone-navigator-constraints.md) for
the full evidence.

| Topology | Native scheduler UI | Sensors | Cloud required |
|---|---|---|---|
| Codec + **paired** Navigator | Yes | Yes (codec) | No |
| **Standalone** Navigator, Control Hub registered | Yes | No | **Yes** — ruled out |
| **Standalone** Navigator, customer managed (`Provisioning Mode: Off`) | No — Persistent Web App only | No | **No** ← chosen |

**Chosen topology: standalone customer-managed Navigator outside the room,
plus a separate in-room RoomOS video device as the occupancy source.** The
panel runs our own Persistent Web App and we drive the LED strip manually with
`UserInterface LedControl Color Set`. The two devices have no native link —
the broker correlates them, replacing the Webex Workspace association.

Per-room device configuration:

```
xCommand Provisioning SetType Type: Standalone
xCommand SystemUnit SetTouchPanelMode Mode: PersistentWebApp
xConfiguration Provisioning Mode: Off
xConfiguration SystemUnit TouchPanel Location: OutsideRoom
xConfiguration UserInterface LedControl Mode: Manual
xConfiguration Security Xapi WebSocket ApiKey Allowed: True
xConfiguration WebEngine Features Xapi Peripherals AllowedHosts Hosts: <broker>
```

On the in-room codec, `xConfiguration RoomAnalytics PeopleCountOutOfCall: On`
is required — it is off by default, and on Codec EQ/Pro it needs a Quad Camera.

---

## 6. Proposed broker design

One reconciliation loop per room, with the calendar as the source of truth and
the device as a cache:

1. **Pull** — authoritative booking window from the calendar driver
   (`calendarView` / sync-token / CalDAV), typically today ± a small window.
2. **Push** — `Bookings Put` with the full list (idempotent, self-healing — a
   full replace on every cycle means device state can never drift
   permanently).
3. **Subscribe** — WebSocket/`HttpFeedback` for `Bookings *` events and
   `RoomAnalytics PeopleCount / PeoplePresence / RoomInUse`.
4. **Write back** — on `BookingRequested`, create the calendar event, then
   confirm or fail on the device.
5. **Occupancy state machine** — reimplement check-in/release logic in the
   broker rather than relying on device config, so the release policy and the
   calendar action stay in one place.

Design notes worth fixing early:

- Make the broker **the organizer of record** for every ad-hoc booking it
  creates. This is the only way it retains the right to genuinely cancel a
  booking later (see calendar-backends.md §"Releasing a booking"). This single
  decision determines whether sensor-driven release actually works or just
  leaves ghosts.
- Keep `Bookings Put` full-replace rather than incremental diffing — far fewer
  failure modes, and the payload is small.
- Treat the device clock seriously: `StartTime` is absolute UTC and the panel
  renders relative to device timezone.
- Default the panel to **busy/free without subject or organizer**, and elevate
  only deliberately. Exchange's own default room-mailbox permission
  (`AvailabilityOnly`) can't even see subjects — a sensible default to mirror
  on a device mounted in a public corridor.

---

## 7. Risks

| Risk | Severity | Notes |
|---|---|---|
| **Commercial-use clause** on `Bookings Put` / equivalents | **High if productised** | Internal business operations = explicitly permitted non-commercial use. Anything "in furtherance of an income-generating service or product" needs written Cisco permission (devsupport@webex.com) |
| Organizer/resource copy asymmetry | **High** | Determines whether "release" really works; drives the organizer-of-record design decision |
| `Bookings Put` unavailable in MTR/Zoom mode | Medium | Excludes Microsoft Teams Rooms devices entirely |
| Standalone panel needs cloud for native UI | Medium | Drives the hardware topology decision |
| Undocumented sensor accuracy/latency | Medium | No published figures; must be characterised in a pilot |
| xAPI schema drift across RoomOS versions | Low–Medium | Pin a minimum RoomOS version; the schema is versioned and public |
| Graph webhooks need a public HTTPS endpoint | Medium | Poll with delta queries instead; EWS streaming is outbound-only |
| Loss of Webex-side features | Low | `Bookings Respond`, cloud analytics, Control Hub config management all go away |

---

## 8. Open questions needing a lab endpoint

- **OQ-1** — **Settled for the Navigator:** customer-managed mode excludes the
  whole `Bookings` family per Cisco's stand-alone guide. The residual test is
  whether that restriction still holds on RoomOS 26, since the guide has not
  been revised since April 2024 while the general schema tags Bookings for the
  Navigator without a caveat. Cheap to test — see stage 1.
- **OQ-2** — Confirm what the native check-in/release flow does at the
  *mailbox protocol* level, to decide whether to mirror it or replace it.
- **OQ-3** — Characterise `PeopleCount` / `PeoplePresence` latency, debounce
  and false-negative behaviour in a real room.
- **OQ-4** — Confirm whether a standalone Navigator in scheduling mode consumes
  a specific Webex licence (no public source found); moot for our path.
- **OQ-5** — Verify the Persistent Web App can bind to the local xAPI via
  `Security Xapi WebSocket ApiKey Allowed` and drive `LedControl Color Set`
  end to end.

## 9. Suggested phasing

1. **Spike** — one Navigator, factory reset, *Set up as standalone → Customer
   managed*, Persistent Web App pointing at a stub page. Prove the web app
   renders, binds to the local xAPI, and that `LedControl Color Set` changes
   the strip. While there, try `SetTouchPanelMode Mode: Scheduler` plus
   `Bookings Put` to settle OQ-1. One afternoon.
2. **Read-only** — Graph driver, one room, calendar → panel. No writes.
3. **Ad-hoc booking** — panel tap → Graph write → confirm.
4. **Occupancy release** — subscribe to the in-room codec, state machine,
   release policy.
5. **Multi-backend + scale** — driver interface, EWS/Google/CalDAV, many rooms,
   management UI.

## Sources

Primary source for all xAPI claims is Cisco's own published schema and TechDocs
repository, [cisco-ce/roomos.cisco.com](https://github.com/cisco-ce/roomos.cisco.com)
(the source behind roomos.cisco.com), specifically `schemas/26.9.1 September
2026.json`, `doc/TechDocs/Integrations.md`, `doc/TechDocs/xAPI.md`,
`doc/TechDocs/UiExtensions.md`, `doc/Features/HttpClient.md`,
`doc/Features/WebAppsOnNavigator.md`, `doc/UseCases/CustomCalendaring.md`, and
`doc/WhatsNew/ReleaseNotesRoomOS_11.md` / `_26.md`.
