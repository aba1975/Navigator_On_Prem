import pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).parent / "img"
OUT.mkdir(parents=True, exist_ok=True)

BASE = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1420px;height:900px;background:#2b2f36;display:flex;align-items:center;justify-content:center;
       font-family:'Inter','Segoe UI',sans-serif;}
  .bezel{width:1360px;height:860px;background:linear-gradient(180deg,#3a3f47,#23262b);border-radius:26px;
         padding:22px;display:flex;gap:14px;box-shadow:0 30px 70px rgba(0,0,0,.55);}
  .led{width:16px;border-radius:9px;align-self:stretch;}
  .led.green {background:linear-gradient(180deg,#5de08a,#16a34a); box-shadow:0 0 28px 6px rgba(34,197,94,.55);}
  .led.red   {background:linear-gradient(180deg,#ff7a63,#dc2626); box-shadow:0 0 28px 6px rgba(220,38,38,.55);}
  .led.amber {background:linear-gradient(180deg,#ffd166,#e0a106); box-shadow:0 0 28px 6px rgba(224,161,6,.55);}
  .screen{flex:1;background:#0f1319;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;position:relative}
  .topbar{display:flex;justify-content:space-between;align-items:flex-start;padding:26px 34px 0 34px;}
  .room{font-size:30px;font-weight:600;color:#fff;letter-spacing:-.2px}
  .roomsub{font-size:17px;color:#8b94a3;margin-top:4px;font-weight:400}
  .chips{display:flex;gap:10px;align-items:center}
  .chip{background:#1c222c;border:1px solid #2a323f;color:#aab3c0;font-size:15px;padding:8px 14px;border-radius:999px;display:flex;gap:7px;align-items:center}
  .dot{width:8px;height:8px;border-radius:50%}
  .body{flex:1;display:flex;padding:22px 34px 0 34px;gap:30px;min-height:0}
  .left{flex:1.25;display:flex;flex-direction:column;justify-content:center;padding-bottom:30px}
  .status{font-size:78px;font-weight:600;letter-spacing:-1.6px;line-height:1}
  .status.g{color:#4ade80}.status.r{color:#f87171}.status.a{color:#fbbf24}
  .sub{font-size:25px;color:#9aa4b2;margin-top:16px;font-weight:400}
  .meeting{font-size:34px;color:#fff;font-weight:500;margin-top:26px}
  .organizer{font-size:20px;color:#8b94a3;margin-top:8px}
  .btns{display:flex;gap:14px;margin-top:40px}
  .btn{background:#19202b;border:1px solid #2c3543;color:#e6eaf0;font-size:21px;font-weight:500;
       padding:20px 30px;border-radius:12px;}
  .btn.primary{background:#2f6fed;border-color:#2f6fed;color:#fff}
  .btn.danger{background:#1f1618;border-color:#4b2326;color:#f3a9a2}
  .agenda{flex:1;background:#141a22;border-radius:14px;padding:24px;margin-bottom:22px;border:1px solid #1e2631}
  .agtitle{font-size:14px;letter-spacing:1.6px;color:#6b7686;font-weight:600;text-transform:uppercase;margin-bottom:18px}
  .ev{display:flex;gap:14px;padding:14px 0;border-bottom:1px solid #1d242f}
  .ev:last-child{border-bottom:none}
  .evbar{width:3px;border-radius:2px;background:#2f6fed}
  .evbar.past{background:#39414d}
  .evbar.now{background:#f87171}
  .evt{font-size:19px;color:#dfe5ec;font-weight:500}
  .evt.past{color:#5d6773}
  .evm{font-size:16px;color:#78828f;margin-top:4px}
  .foot{display:flex;justify-content:space-between;align-items:center;padding:0 34px 24px 34px;color:#6b7686;font-size:17px}
  .pill{padding:7px 16px;border-radius:999px;font-size:15px;font-weight:600}
  .banner{position:absolute;left:0;right:0;bottom:0;padding:26px 34px;display:flex;align-items:center;justify-content:space-between;
          background:linear-gradient(90deg,#2a2208,#3a2d06);border-top:1px solid #5c4708}
  .bantxt{font-size:23px;color:#ffd77a;font-weight:500}
  .bansub{font-size:17px;color:#b79a53;margin-top:5px}
</style>
"""


def panel(led, status_cls, status, sub, extra_left, chips, agenda, foot_pill, banner=""):
    return f"""<html><head>{BASE}</head><body>
    <div class="bezel">
      <div class="led {led}"></div>
      <div class="screen">
        <div class="topbar">
          <div><div class="room">Nordlys</div><div class="roomsub">3rd floor &middot; north wing</div></div>
          <div class="chips">{chips}</div>
        </div>
        <div class="body">
          <div class="left">
            <div class="status {status_cls}">{status}</div>
            <div class="sub">{sub}</div>
            {extra_left}
          </div>
          <div class="agenda"><div class="agtitle">Today</div>{agenda}</div>
        </div>
        <div class="foot"><div>Wednesday 8 October &middot; 14:05</div>{foot_pill}</div>
        {banner}
      </div>
      <div class="led {led}"></div>
    </div></body></html>"""


CHIPS_OK = ('<div class="chip"><span class="dot" style="background:#4ade80"></span>8 seats</div>'
            '<div class="chip">21.5&deg;C</div>'
            '<div class="chip"><span class="dot" style="background:#4ade80"></span>0 people</div>')
CHIPS_BUSY = ('<div class="chip"><span class="dot" style="background:#4ade80"></span>8 seats</div>'
              '<div class="chip">22.8&deg;C</div>'
              '<div class="chip"><span class="dot" style="background:#f87171"></span>5 people</div>')
CHIPS_EMPTY = ('<div class="chip"><span class="dot" style="background:#4ade80"></span>8 seats</div>'
               '<div class="chip">21.9&deg;C</div>'
               '<div class="chip"><span class="dot" style="background:#fbbf24"></span>0 people</div>')

AG_AVAIL = """
<div class="ev"><div class="evbar past"></div><div><div class="evt past">Design review</div><div class="evm">09:00 &ndash; 10:00 &middot; Kari Nordmann</div></div></div>
<div class="ev"><div class="evbar"></div><div><div class="evt">Sprint planning</div><div class="evm">16:20 &ndash; 17:00 &middot; Ola Hansen</div></div></div>
"""
AG_BUSY = """
<div class="ev"><div class="evbar past"></div><div><div class="evt past">Design review</div><div class="evm">09:00 &ndash; 10:00 &middot; Kari Nordmann</div></div></div>
<div class="ev"><div class="evbar now"></div><div><div class="evt">Quarterly planning</div><div class="evm">14:00 &ndash; 15:00 &middot; Anders Abrahamsen</div></div></div>
<div class="ev"><div class="evbar"></div><div><div class="evt">Sprint planning</div><div class="evm">16:20 &ndash; 17:00 &middot; Ola Hansen</div></div></div>
"""

pages = {
    "panel_available.png": panel(
        "green", "g", "Available", "for the next 1 h 55 min",
        '<div class="btns"><div class="btn primary">Book 15 min</div><div class="btn">30 min</div><div class="btn">1 hour</div></div>',
        CHIPS_OK, AG_AVAIL,
        '<div class="pill" style="background:#10281a;color:#4ade80">&#9679; Available</div>'),

    "panel_inuse.png": panel(
        "red", "r", "In use", "ends in 55 min &middot; 14:00 &ndash; 15:00",
        '<div class="meeting">Quarterly planning</div><div class="organizer">Anders Abrahamsen &middot; checked in 14:01</div>'
        '<div class="btns"><div class="btn">Extend 15 min</div><div class="btn danger">End &amp; release</div></div>',
        CHIPS_BUSY, AG_BUSY,
        '<div class="pill" style="background:#2a1416;color:#f87171">&#9679; In use</div>'),

    "panel_checkin.png": panel(
        "amber", "a", "Starting now", "Quarterly planning &middot; 14:00 &ndash; 15:00",
        '<div class="organizer" style="margin-top:22px">Anders Abrahamsen</div>'
        '<div class="btns"><div class="btn primary">Check in</div><div class="btn danger">Release room</div></div>',
        CHIPS_EMPTY, AG_BUSY,
        '<div class="pill" style="background:#2a2208;color:#fbbf24">&#9679; Awaiting check-in</div>',
        '<div class="banner"><div><div class="bantxt">Room will be released in 6:42</div>'
        '<div class="bansub">No people detected since the meeting started</div></div>'
        '<div class="pill" style="background:#3a2d06;color:#ffd77a;font-size:17px;padding:12px 22px">Auto-release armed</div></div>'),
}

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1420, "height": 900}, device_scale_factor=2)
    for name, html in pages.items():
        pg.set_content(html)
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / name))
        print("wrote", name)
    b.close()
