# Calendar back-ends

The device side is the easy half. The calendar side is where the genuinely hard
problems live — in particular, "release the room" is not a simple delete.

---

## 1. Microsoft Graph (Exchange Online) — primary target

### Discovery and auth

- Rooms live in the **Places API**: `GET /places/microsoft.graph.room`, or per
  room list `GET /places/{roomlist-email}/microsoft.graph.roomlist/rooms` (room
  lists are addressed by **email, not id**). The `room` resource carries
  `emailAddress`, `capacity`, `building`, `floorNumber`, `videoDeviceName` and
  `bookingType` (`standard` = reservable, `reserved` = not bookable by invite).
- A daemon uses the **client-credentials (app-only)** flow with application
  permissions: `Place.Read.All` plus `Calendars.ReadWrite`.

### Scoping — do not skip this

By default an app-only credential with `Calendars.ReadWrite` can read and write
**every mailbox in the tenant**. There is no room-level restriction at the
Entra consent layer. Two mechanisms fix it:

- **Legacy**: `New-ApplicationAccessPolicy -AccessRight RestrictAccess -AppId
  <id> -PolicyScopeGroupId <room-group>`. Note the evaluation rule: once an app
  has *any* `RestrictAccess` policy, mailboxes outside it are denied by
  default. Applies to Graph *and* EWS.
- **Current**: **RBAC for Applications** — Microsoft states it *"replaces
  Application Access Policies"*, and the legacy cmdlet now carries a "don't
  create new ones" banner. Register the service principal in Exchange, define a
  `New-ManagementScope` over the room mailboxes, and assign a narrow role:

  ```powershell
  New-ManagementRoleAssignment -App <ServicePrincipalObjectId> `
      -Role "Application Calendars.ReadWrite" -CustomResourceScope "Meeting Rooms"
  ```

  `Test-ServicePrincipalAuthorization` simulates the result. Allow 30 min–2 hrs
  for cache propagation.

**Build against RBAC for Applications.** It is also a materially better privacy
story than Hybrid Calendar's tenant-wide "read/write calendars in all
mailboxes" consent.

### Reading

- Use **`calendarView`**, not `events`. `calendarView` returns occurrences
  already expanded for the window, including modified exceptions. `events`
  returns series masters, which a panel cannot render correctly.
- `calendarView/delta` gives incremental sync via `@odata.deltaLink` — one
  delta stream per room, scoped to one calendar and date range.
- `Prefer: outlook.timezone="..."` to avoid doing UTC conversion yourself.
- `POST /users/{x}/calendar/getSchedule` checks free/busy across many rooms in
  one call — useful for "find me a free room".
- **`findMeetingTimes` does not support application permissions at all.** It is
  delegated-only; a daemon must build slot suggestion on `getSchedule`.

### Change notification — the on-prem problem

Graph webhooks require a **publicly accessible HTTPS endpoint**; Microsoft is
explicit that notifications are simply not sent otherwise. Azure Event
Hubs/Event Grid are the alternatives, but both reintroduce cloud infrastructure
— contrary to the point of this project.

**For an on-prem broker, poll with delta queries** (1–5 min interval). Latency
is bounded by the interval, which is acceptable for room booking. Note also:

- Subscriptions must be renewed before `expirationDateTime`; nothing is
  indefinite.
- Basic notifications carry only an id — a follow-up read is needed anyway
  unless you opt into encrypted rich notifications.
- Graph marks endpoints "slow" past a 3 s response time and drops notifications
  past 10 s — another reason polling is the lower-risk choice here.

Global ceiling is 130,000 requests / 10 s per app; `429` + `Retry-After` is the
backoff signal. The exact per-mailbox Calendars limit is not clearly published
— load-test before committing to an interval across hundreds of rooms.

### Creating a booking

Two options, and the choice has real consequences:

**Option A (recommended)** — create the event **as an organizer** with the room
as attendee (`type: resource`) and location. It then flows through Exchange's
normal meeting-request pipeline, and the room's **resource booking attendant**
arbitrates per its configured policy (`AllowConflicts`, `BookingWindowInDays`,
`ConflictPercentageAllowed`, `ProcessExternalMeetingMessages`,
`BookInPolicy`…).

**Option B** — write directly into the room mailbox's own calendar. This
**bypasses the resource booking attendant entirely**, because the policy engine
processes *incoming iTIP messages*, not arbitrary calendar writes. You can
silently double-book a room configured to reject conflicts, and there is no
organizer copy anywhere, so nobody can see who booked it or why.

Use Option A. Letting Exchange arbitrate also closes the double-booking race
between a panel tap and a simultaneous Outlook booking — a race your own
read-then-write logic cannot close atomically.

### Releasing a booking — the hardest part

There is **one master copy** (the organizer's) and **N attendee copies**
(including the room's). A daemon acting as the room can only touch the room's
copy:

- `event: cancel` is **organizer-only**.
- `event: decline` is the attendee action. The room declines **its own copy**.
  This frees the room's calendar, and notifies the organizer — but **the
  organizer's meeting still exists**, still says "Conference Room X", and
  Exchange may even attempt to reprocess the room booking if the organizer
  later edits it.
- **Shortening** the room's copy diverges it from the master, which anchors
  free/busy. Don't.

So a "release" implementation has exactly three honest choices:

1. **Decline the room's copy** — simple, matches Exchange semantics, accepts
   that the organizer sees a ghost meeting until they notice the decline.
2. **Be the organizer** — if the broker creates every ad-hoc booking as
   organizer of record, it can genuinely `cancel` them. Works only for bookings
   your system created, not for Outlook/Teams meetings where the room is merely
   an attendee.
3. **Use Exchange's native auto-release** — `Set-CalendarProcessing -Identity
   <room> -EnableAutoRelease $true -PostReservationMaxClaimTimeInMinutes 20`
   makes Exchange itself release a room nobody checked into. Server-side logic
   you don't have to write — but it is check-in-driven, so you'd need to feed
   occupancy into it as a "check-in".

**Recommendation: (2) for your own bookings, (1) for everyone else's, and be
explicit in the UX about the difference.** This is the design decision that
most affects whether the product feels correct.

---

## 2. Exchange on-premises — EWS

- **EWS** (SOAP, or the Managed API) is the path; Graph does not reach on-prem
  mailboxes.
- Use **impersonation**, not delegation, for many room mailboxes. The
  `ApplicationImpersonation` RBAC role **must** be paired with a management
  scope — otherwise, in Microsoft's own words, *"the ApplicationImpersonation
  role is granted to all accounts in an organization."* Same trap as Graph.
- Auth is NTLM/Kerberos; OAuth is Exchange Online only.
- **Streaming notifications** hold a long-lived outbound connection (~30 min)
  and push changes over it — **no public endpoint required**. This makes EWS
  *more* on-prem-friendly than Graph for change detection. Prefer streaming
  over pull; push notifications are legacy.

**Deprecation**: EWS is being retired in **Exchange Online (October 2026)**.
This does not remove on-prem Exchange Server's own EWS endpoint. The
implication is architectural: build Exchange Online on **Graph**, and treat EWS
as the **on-prem-only driver**. A single EWS client for both is not viable.

---

## 3. Google Workspace

- Rooms are calendar **resources** (Admin SDK Directory API
  `resources.calendars`), each with an email address that doubles as its
  Calendar API calendar ID.
- Auth: **service account with domain-wide delegation**, JWT → OAuth token,
  scopes restricted in the Admin console. Coarser than Exchange RBAC — you
  can restrict scopes but not naturally restrict to a room list.
- Same organizer/attendee master-copy model as Exchange, so §1's release
  asymmetry applies identically.
- Push `watch` channels need a public HTTPS endpoint with a CA-signed cert
  (same problem as Graph) and carry no payload. **Use incremental sync tokens
  instead** — `nextSyncToken`, with `410 Gone` meaning "full resync".
- Quota: 10,000 req/min per project, 600 req/min per user per project.

---

## 4. CalDAV / self-hosted groupware

- **RFC 4791** covers storage; **RFC 6638** adds scheduling (Outbox/Inbox
  collections, iTIP-style invitation flow). Only the latter gives you anything
  resembling resource booking.
- **Nextcloud** has a Calendar Resource Management app modelling buildings →
  floors → rooms, each with a uid and email address, managed via `occ
  calendar-resource:*`, plus FreeBusy support in its CalDAV server.
- **SOGo** implements CalDAV scheduling and has resource accounts with
  configurable auto-accept (specific parameter names not verified here).
- **Radicale is storage only.** Its documentation has no mention of scheduling,
  free/busy, auto-accept or resource semantics. Point it at a room calendar and
  you get a dumb collection with **zero server-side conflict checking** — 100%
  of booking policy would have to live in the broker.

---

## 5. Comparison

| Back end | Change detection | Ad-hoc write | Release / shorten | Auth | On-prem friendly |
|---|---|---|---|---|---|
| **Exchange Online (Graph)** | Webhooks need public HTTPS; **delta polling** otherwise | Organizer + room as resource | Decline room's copy; cancel only if organizer; native `EnableAutoRelease` exists | App-only + **RBAC for Applications** | Medium — polling works fine |
| **Exchange on-prem (EWS)** | **Streaming (outbound only)** | Same pattern via `CreateItem` | Same asymmetry | `ApplicationImpersonation` + **scoped** | **Good** |
| **Google Workspace** | `watch` needs public HTTPS; **sync tokens** otherwise | Direct to resource calendar, or as attendee | Same asymmetry | Service account + DWD | Medium |
| **CalDAV (Nextcloud/SOGo)** | Polling (ctag/etag/`sync-collection`) | RFC 6638 scheduling or app abstraction | App-implementation dependent | Basic / app password / OAuth | **Best** |
| **Radicale** | Polling only | Plain iCalendar `PUT` | Entirely your problem | Pluggable | Best connectivity, **worst** semantics |

---

## 6. Pitfalls to design for

- **Organizer vs. resource divergence** — the single biggest one. See §1.
- **Recurring exceptions** — a series can have individually moved, shortened or
  cancelled occurrences. Always resolve against expanded `calendarView` /
  `instances`, never project from the recurrence rule.
- **Double-booking races** — panel tap vs. Outlook booking. Route through the
  native resource attendant rather than read-then-write.
- **Clock skew** — subscription renewals, streaming keep-alives and booking
  windows are all time-bounded. NTP on the broker host is mandatory, and the
  device clock matters too.
- **Privacy on a wall-mounted panel** — check Graph `sensitivity` / Google
  `visibility` before rendering a subject. Default to busy/free only. Showing
  "Booked by Jane Doe" in a public corridor is a new processing purpose beyond
  the original calendar entry, and worth a deliberate, configurable decision
  rather than an accidental default. The broker's own "who released what, when"
  logs are personal data too, and need a retention policy.

## Sources

Microsoft Learn (Places API, permissions reference, `New-ApplicationAccessPolicy`,
Exchange application RBAC, `calendarView`, delta query, change notifications,
throttling, `Set-CalendarProcessing`, EWS impersonation and notifications,
Microsoft Places auto-release), Google Workspace developer documentation
(Calendar API events/push/sync/quota, service-account OAuth), RFC 4791 / RFC
6638, and Nextcloud / SOGo / Radicale project documentation.
