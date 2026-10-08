import pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).parent / "img"
OUT.mkdir(parents=True, exist_ok=True)

CSS = """
<style>
 @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
 *{margin:0;padding:0;box-sizing:border-box}
 body{width:1680px;height:1020px;background:#aeb4bd;font-family:'Inter','Segoe UI',sans-serif;
      display:flex;align-items:center;justify-content:center}
 .win{width:1640px;height:990px;background:#f4f6f8;border-radius:12px;overflow:hidden;
      box-shadow:0 26px 60px rgba(0,0,0,.4);display:flex;flex-direction:column}
 .chrome{height:48px;background:#e3e7ec;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid #d2d8df}
 .tl{display:flex;gap:7px}.tl i{width:12px;height:12px;border-radius:50%;display:block}
 .url{flex:1;background:#fff;border:1px solid #d2d8df;border-radius:7px;height:30px;display:flex;align-items:center;
      padding:0 12px;font-size:13px;color:#55616f;gap:8px}
 .main{flex:1;display:flex;min-height:0}
 .side{width:232px;background:#111826;padding:22px 0;display:flex;flex-direction:column;gap:3px}
 .brand{color:#fff;font-size:17px;font-weight:700;padding:0 22px 22px 22px;display:flex;align-items:center;gap:10px}
 .blogo{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,#3b82f6,#22c55e)}
 .nav{color:#8c97a8;font-size:14.5px;padding:11px 22px;display:flex;gap:11px;align-items:center}
 .nav.on{color:#fff;background:#1c2738;border-left:3px solid #3b82f6;padding-left:19px;font-weight:500}
 .navsec{color:#5b6677;font-size:11px;letter-spacing:1.3px;font-weight:600;padding:18px 22px 7px}
 .content{flex:1;padding:26px 30px;overflow:hidden;position:relative}
 .h1{font-size:23px;font-weight:600;color:#17202e}
 .sub{font-size:13.5px;color:#6b7684;margin-top:4px}
 .hdr{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px}
 .btn{background:#2563eb;color:#fff;font-size:13.5px;font-weight:500;padding:10px 17px;border-radius:7px}
 .btn.ghost{background:#fff;color:#394350;border:1px solid #d2d8df}
 table{width:100%;border-collapse:collapse;background:#fff;border-radius:9px;overflow:hidden;
       box-shadow:0 1px 3px rgba(16,24,40,.08);border:1px solid #e3e7ec}
 th{text-align:left;font-size:11px;letter-spacing:.8px;color:#78828f;text-transform:uppercase;
    padding:12px 16px;background:#f8fafc;border-bottom:1px solid #e3e7ec;font-weight:600}
 td{padding:13px 16px;font-size:13.5px;color:#2b3542;border-bottom:1px solid #eef1f4}
 tr:last-child td{border-bottom:none}
 .mono{font-family:'Cascadia Mono',Consolas,monospace;font-size:12.5px;color:#55616f}
 .tag{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:4px 10px;border-radius:999px}
 .ok{background:#e8f8ee;color:#15803d}.warn{background:#fef6e7;color:#b45309}.off{background:#eef1f4;color:#6b7684}
 .d{width:7px;height:7px;border-radius:50%;background:currentColor}
 .scrim{position:absolute;inset:0;background:rgba(17,24,38,.55)}
 .modal{position:absolute;left:50%;top:46%;transform:translate(-50%,-50%);width:1020px;background:#fff;border-radius:13px;
        box-shadow:0 30px 70px rgba(0,0,0,.35);overflow:hidden}
 .mh{padding:20px 26px;border-bottom:1px solid #e9edf1;display:flex;justify-content:space-between;align-items:center}
 .mt{font-size:18px;font-weight:600;color:#17202e}
 .mb{padding:22px 26px;display:flex;flex-direction:column;gap:14px}
 .card{border:1px solid #e3e7ec;border-radius:10px;padding:16px 18px;display:flex;gap:15px;background:#fcfdfe}
 .num{width:26px;height:26px;border-radius:50%;background:#2563eb;color:#fff;font-size:13px;font-weight:600;
      display:flex;align-items:center;justify-content:center;flex:none;margin-top:2px}
 .ct{font-size:14.5px;font-weight:600;color:#17202e;margin-bottom:3px}
 .cs{font-size:12.5px;color:#78828f;margin-bottom:11px}
 .row{display:flex;gap:10px;align-items:center}
 .inp{flex:1;border:1px solid #d2d8df;border-radius:7px;padding:8px 11px;font-size:13px;color:#2b3542;background:#fff}
 .inp.k{font-family:'Cascadia Mono',Consolas,monospace;font-size:12.5px}
 .probe{margin-top:10px;background:#f1f8f4;border:1px solid #cfe9da;border-radius:7px;padding:9px 12px;
        font-size:12.5px;color:#1c6b43;display:flex;flex-wrap:wrap;gap:x;gap:14px}
 .probe b{font-weight:600}
 .mf{padding:16px 26px;border-top:1px solid #e9edf1;display:flex;justify-content:space-between;align-items:center;background:#fafbfc}
 .hint{font-size:12.5px;color:#78828f}
 .pol{display:flex;gap:10px;align-items:center;font-size:13px;color:#2b3542}
 .sel{border:1px solid #d2d8df;border-radius:7px;padding:7px 10px;font-size:13px;background:#fff}
</style>
"""

HTML = f"""<html><head>{CSS}</head><body><div class="win">
 <div class="chrome">
   <div class="tl"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
   <div class="url">&#128274; https://roombooking.corp.local/rooms</div>
 </div>
 <div class="main">
  <div class="side">
    <div class="brand"><div class="blogo"></div>Room Broker</div>
    <div class="nav">Dashboard</div>
    <div class="nav on">Rooms</div>
    <div class="nav">Devices</div>
    <div class="navsec">INTEGRATIONS</div>
    <div class="nav">Calendar sources</div>
    <div class="nav">Policies</div>
    <div class="navsec">SYSTEM</div>
    <div class="nav">Activity log</div>
    <div class="nav">Settings</div>
  </div>
  <div class="content">
    <div class="hdr">
      <div><div class="h1">Rooms</div><div class="sub">4 rooms &middot; 8 devices &middot; calendar source: Exchange Online (Microsoft Graph)</div></div>
      <div class="btn">+ Pair room</div>
    </div>
    <table>
      <tr><th>Room</th><th>Booking panel</th><th>Video device (sensors)</th><th>Mailbox</th><th>Status</th></tr>
      <tr><td><b>Nordlys</b><div class="mono">3rd floor</div></td>
          <td class="mono">10.14.2.31<div style="color:#9aa3ae">Navigator &middot; PWA</div></td>
          <td class="mono">10.14.2.30<div style="color:#9aa3ae">Room Bar Pro</div></td>
          <td class="mono">nordlys@contoso.com</td>
          <td><span class="tag ok"><span class="d"></span>Paired</span></td></tr>
      <tr><td><b>Fjord</b><div class="mono">2nd floor</div></td>
          <td class="mono">10.14.2.41<div style="color:#9aa3ae">Navigator &middot; PWA</div></td>
          <td class="mono">10.14.2.40<div style="color:#9aa3ae">Room Kit EQ</div></td>
          <td class="mono">fjord@contoso.com</td>
          <td><span class="tag ok"><span class="d"></span>Paired</span></td></tr>
      <tr><td><b>Vidde</b><div class="mono">2nd floor</div></td>
          <td class="mono">10.14.2.51<div style="color:#9aa3ae">Navigator &middot; PWA</div></td>
          <td class="mono">&mdash;</td>
          <td class="mono">vidde@contoso.com</td>
          <td><span class="tag warn"><span class="d"></span>No sensors</span></td></tr>
      <tr><td><b>Tundra</b><div class="mono">1st floor</div></td>
          <td class="mono">10.14.2.61<div style="color:#9aa3ae">Navigator &middot; PWA</div></td>
          <td class="mono">10.14.2.60<div style="color:#9aa3ae">Room Bar</div></td>
          <td class="mono">&mdash;</td>
          <td><span class="tag off"><span class="d"></span>Unlinked</span></td></tr>
    </table>

    <div class="scrim"></div>
    <div class="modal">
      <div class="mh"><div class="mt">Pair room &mdash; Tundra</div><div class="hint">Step 3 of 3</div></div>
      <div class="mb">

        <div class="card"><div class="num">1</div><div style="flex:1">
          <div class="ct">Booking panel &middot; Room Navigator</div>
          <div class="cs">Must be customer managed (<span class="mono">Provisioning Mode: Off</span>) and in Persistent Web App mode.</div>
          <div class="row"><input class="inp k" value="10.14.2.61"><input class="inp k" value="admin">
            <input class="inp k" value="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"><div class="btn ghost">Test</div></div>
          <div class="probe"><span><b>Room Navigator</b> RoomOS 26.9.1</span>
            <span>&#10003; Provisioning Mode: Off</span><span>&#10003; TouchPanel Mode: PersistentWebApp</span>
            <span>&#10003; LedControl Mode: Manual</span><span>&#10003; Location: OutsideRoom</span></div>
        </div></div>

        <div class="card"><div class="num">2</div><div style="flex:1">
          <div class="ct">Video device &middot; occupancy source</div>
          <div class="cs">Supplies people count and in-use state over local xAPI. Optional &mdash; without it, release falls back to check-in only.</div>
          <div class="row"><input class="inp k" value="10.14.2.60"><input class="inp k" value="integrator">
            <input class="inp k" value="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"><div class="btn ghost">Test</div></div>
          <div class="probe"><span><b>Room Bar</b> RoomOS 26.9.1</span>
            <span>&#10003; RoomAnalytics PeopleCountOutOfCall: On</span>
            <span>&#10003; PeoplePresenceDetector: On</span><span>&#10003; People now: 0</span></div>
        </div></div>

        <div class="card"><div class="num">3</div><div style="flex:1">
          <div class="ct">Calendar &middot; room mailbox</div>
          <div class="cs">Discovered from Microsoft Graph Places API. The broker is organizer of record for ad-hoc bookings.</div>
          <div class="row"><select class="sel" style="flex:1"><option>tundra@contoso.com &mdash; Tundra (1st floor, 6 seats)</option></select>
            <div class="btn ghost">Re-scan</div></div>
          <div class="probe"><span>&#10003; Graph app-only token valid</span><span>&#10003; Scoped via RBAC for Applications</span>
            <span>&#10003; Calendars.ReadWrite on this mailbox</span><span>&#10003; 3 events today</span></div>
        </div></div>

        <div class="row" style="gap:22px;padding:2px 2px 0 2px">
          <div class="pol">Check-in window <select class="sel"><option>10 min</option></select></div>
          <div class="pol">Release if empty for <select class="sel"><option>15 min</option></select></div>
          <div class="pol">Panel shows <select class="sel"><option>Title &amp; organizer</option></select></div>
        </div>
      </div>
      <div class="mf"><div class="hint">Web app URL will be pushed to the panel on save.</div>
        <div class="row"><div class="btn ghost">Cancel</div><div class="btn">Pair room</div></div></div>
    </div>
  </div>
 </div>
</div></body></html>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1680, "height": 1020}, device_scale_factor=2)
    pg.set_content(HTML)
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT / "admin_pair.png"))
    print("wrote admin_pair.png")
    b.close()
