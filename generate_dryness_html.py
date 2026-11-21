"""Generate build_outputs_folder/dryness.html - "Is the rock dry?" page.

Reuses climbing-locations.json (crags, drive time, multipitch type) from the
main crag-weather page, and adds a per-crag rock-wetness model driven by
Open-Meteo hourly data (past 5 days + next 5 days).

Run:  python generate_dryness_html.py            (live data, used by the Action)
      python generate_dryness_html.py --sample   (synthetic weather, for offline preview)
"""
import json
import math
import random
import sys
import time
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

import requests

LOCATIONS_FILE = 'climbing-locations.json'
PROFILES_FILE = 'crag-profiles.json'
OUTPUT_FILE = 'build_outputs_folder/dryness.html'
TIMEZONE = 'Europe/Zagreb'
PAST_DAYS = 5
FORECAST_DAYS = 5
CHECK_HOUR = 11          # the hour of each day we report ("is it dry at 11:00?")
MAX_WATER = 3.0          # mm - water a wall holds; the rest runs off

HOURLY_VARS = ['temperature_2m', 'relative_humidity_2m', 'dew_point_2m',
               'precipitation', 'wind_speed_10m', 'shortwave_radiation']

# How quickly each rock type sheds water relative to compact limestone.
ROCK_FACTOR = {'limestone': 1.0, 'granite': 1.2, 'gneiss': 1.2,
               'conglomerate': 0.75, 'sandstone': 0.6}
SOFT_ROCK = {'sandstone'}  # climbing it wet damages it

def local_now():
    return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)


DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


# ---------------------------------------------------------------- inputs

def load_crags():
    with open(LOCATIONS_FILE) as f:
        locations = json.load(f)
    try:
        with open(PROFILES_FILE) as f:
            profiles = json.load(f)
    except FileNotFoundError:
        profiles = {}
    defaults = {'aspect': None, 'rock': 'limestone', 'steep': False, 'seeps': False}
    defaults.update(profiles.get('_defaults', {}))
    crags = {}
    for name, loc in locations.items():
        p = dict(defaults)
        p.update(profiles.get(name, {}))
        p['profiled'] = name in profiles
        crags[name] = {**loc, 'profile': p}
    return crags


def fetch_weather(crags):
    names = list(crags)
    lats = ','.join(str(round(crags[n]['location'][0], 4)) for n in names)
    lons = ','.join(str(round(crags[n]['location'][1], 4)) for n in names)
    url = ('https://api.open-meteo.com/v1/forecast'
           f'?latitude={lats}&longitude={lons}'
           f'&hourly={",".join(HOURLY_VARS)}'
           f'&past_days={PAST_DAYS}&forecast_days={FORECAST_DAYS}'
           f'&wind_speed_unit=ms&timezone={TIMEZONE}')
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60,
                             headers={'User-Agent': 'crag-weather/1.0 (github.com/paitty/crag-weather)'})
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                data = [data]
            return {n: d['hourly'] for n, d in zip(names, data)}
        except Exception as e:
            print(f'[dryness] open-meteo attempt {attempt+1} failed: {e}')
            time.sleep(5)
    raise RuntimeError('Open-Meteo unreachable')


def sample_weather(crags):
    """Synthetic but plausible weather, so the page can be previewed offline."""
    start = local_now().replace(minute=0, second=0, microsecond=0, hour=0) - timedelta(days=PAST_DAYS)
    hours = [start + timedelta(hours=h) for h in range((PAST_DAYS + FORECAST_DAYS) * 24)]
    out = {}
    for i, name in enumerate(crags):
        rnd = random.Random(i)
        storm_at = rnd.randint(40, 150)          # hour index of a rain event
        storm_mm = rnd.choice([0, 3, 8, 15, 30])
        h = {k: [] for k in HOURLY_VARS}
        h['time'] = [t.strftime('%Y-%m-%dT%H:%M') for t in hours]
        for j, t in enumerate(hours):
            day = max(0.0, math.sin(math.pi * (t.hour - 6) / 12)) if 6 <= t.hour <= 18 else 0.0
            raining = storm_at <= j < storm_at + 6 and storm_mm
            temp = 6 + 7 * day + rnd.uniform(-1, 1) - (2 if raining else 0)
            rh = 95 if raining else max(45, 88 - 35 * day + rnd.uniform(-5, 5))
            h['temperature_2m'].append(round(temp, 1))
            h['relative_humidity_2m'].append(round(rh))
            h['dew_point_2m'].append(round(temp - (100 - rh) / 5, 1))
            h['precipitation'].append(round(storm_mm / 6, 1) if raining else 0.0)
            h['wind_speed_10m'].append(round(rnd.uniform(0.5, 5), 1))
            h['shortwave_radiation'].append(round(0 if raining else 450 * day * rnd.uniform(0.5, 1)))
        out[name] = h
    return out


# ---------------------------------------------------------------- model

def sat_vapour_pressure(t):
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))  # kPa


def sun_factor(aspect, hour):
    """Share of the sun's drying a wall gets, by aspect and time of day."""
    if aspect is None:
        return 0.5   # average over all directions
    a = aspect.upper()
    morning = hour < 12
    table = {
        'S': 1.0, 'SE': 1.0 if morning else 0.6, 'SW': 0.6 if morning else 1.0,
        'E': 0.9 if morning else 0.15, 'W': 0.15 if morning else 0.9,
        'NE': 0.4 if morning else 0.05, 'NW': 0.05 if morning else 0.4, 'N': 0.05,
    }
    return table.get(a, 0.5)


def run_model(hourly, profile):
    """Hour-by-hour water balance on the rock surface.

    water += rain reaching the wall (less on steep/sheltered walls)
    water += condensation when air is at dew point and there is no sun
    water -= evaporation, driven by vapour-pressure deficit, wind and sun on that aspect
    Returns list of (time, water_mm, score) plus per-hour drivers.
    """
    rock = ROCK_FACTOR.get(profile['rock'], 1.0)
    rain_share = 0.2 if profile['steep'] else 1.0
    water = 0.0
    rows = []
    for i, ts in enumerate(hourly['time']):
        t = datetime.fromisoformat(ts)
        temp = hourly['temperature_2m'][i] or 0
        rh = hourly['relative_humidity_2m'][i] or 0
        dew = hourly['dew_point_2m'][i] if hourly['dew_point_2m'][i] is not None else temp - 5
        rain = hourly['precipitation'][i] or 0
        wind = hourly['wind_speed_10m'][i] or 0
        sw = hourly['shortwave_radiation'][i] or 0

        water += rain * rain_share
        if temp - dew < 1.0 and sw < 50:
            water += 0.03                         # condensation / "sweating" rock
        vpd = sat_vapour_pressure(temp) * (1 - rh / 100)
        evap = 0.25 * vpd * (1 + 0.15 * min(wind, 10))
        evap += 0.0012 * sw * sun_factor(profile['aspect'], t.hour)
        if temp < 0:
            evap *= 0.3                           # frozen / very slow drying
        water = min(MAX_WATER, max(0.0, water - evap * rock))
        score = round(100 * math.exp(-water / 0.8))
        rows.append({'time': t, 'water': water, 'score': score, 'rain': rain})
    return rows


def status(score):
    if score >= 75:
        return 'dry', '✅', 'Dry'
    if score >= 40:
        return 'damp', '🟡', 'Damp'
    return 'wet', '💧', 'Wet'


def explain(rows, idx, profile):
    """Short human reason for the value at rows[idx]."""
    now = rows[idx]['time']
    past = [r for r in rows[:idx + 1] if r['time'] > now - timedelta(hours=72)]
    rain72 = sum(r['rain'] for r in past)
    last_rain = next((r['time'] for r in reversed(past) if r['rain'] >= 0.3), None)
    bits = []
    if rain72 < 0.5:
        bits.append('no rain in 72h')
    else:
        ago = int((now - last_rain).total_seconds() // 3600) if last_rain else None
        bits.append(f'{rain72:.0f} mm in 72h' + (f', last {ago}h before' if ago is not None else ''))
    if profile['aspect']:
        bits.append(f"{profile['aspect']}-facing")
    if profile['steep']:
        bits.append('steep/sheltered')
    if profile['rock'] != 'limestone':
        bits.append(profile['rock'])
    warn = []
    if profile['seeps'] and rain72 > 20:
        warn.append('seepage likely')
    if profile['rock'] in SOFT_ROCK and rain72 > 0.5:
        warn.append('soft rock - wait 24-48h')
    return ', '.join(bits), warn, rain72


# ---------------------------------------------------------------- page

def fmt_drive(minutes):
    total = int(int(minutes) / 10) * 10
    h, m = divmod(total, 60)
    return f'{m} min' if h == 0 else f'{h}h{m}m'


def build_rows(crags, weather):
    today = local_now().replace(minute=0, second=0, microsecond=0)
    check_days = [(today + timedelta(days=d)).replace(hour=CHECK_HOUR) for d in range(FORECAST_DAYS)]
    result = []
    for name, crag in crags.items():
        if name not in weather:
            continue
        rows = run_model(weather[name], crag['profile'])
        index = {r['time']: i for i, r in enumerate(rows)}
        cells = []
        for d in check_days:
            i = index.get(d)
            if i is None:
                cells.append(None)
                continue
            why, warn, _ = explain(rows, i, crag['profile'])
            cells.append({'score': rows[i]['score'], 'why': why, 'warn': warn})
        now_i = index.get(today, None)
        _, _, rain72 = explain(rows, now_i, crag['profile']) if now_i is not None else ('', [], 0)
        result.append({'name': name, 'crag': crag, 'cells': cells, 'rain72': rain72})
    return check_days, result


def weekend_best(check_days, crag_rows):
    """Best crag for the coming Sat/Sun: driest, then closest."""
    idx = [i for i, d in enumerate(check_days) if d.weekday() >= 5] or [0]
    best = None
    for row in crag_rows:
        for i in idx:
            c = row['cells'][i]
            if not c:
                continue
            key = (c['score'] >= 75, c['score'] - 0.1 * row['crag'].get('Distance', 0))
            if best is None or key > best[0]:
                best = (key, row['name'], check_days[i])
    return best


def render(check_days, crag_rows, source_note):
    best = weekend_best(check_days, crag_rows)
    first_weekend = next((i for i, d in enumerate(check_days) if d.weekday() >= 5), 0)
    crag_rows.sort(key=lambda r: (-(r['cells'][first_weekend] or {'score': 0})['score'],
                                  r['crag'].get('Distance', 0)))
    updated = local_now().strftime('%d/%m/%Y %H:%M')

    head_days = ''.join(
        f'<th onclick="sortTable({i+1})" class="{"wk" if d.weekday() >= 5 else ""}">'
        f'{DAYS[d.weekday()]} {d.day}.</th>' for i, d in enumerate(check_days))
    n = len(check_days)

    body = []
    for row in crag_rows:
        crag, name = row['crag'], row['name']
        lat, lon = crag['location']
        park = crag.get('parking', crag['location'])
        slug = name.replace('(', '').replace(')', '').replace(' ', '-').lower()
        tds = [f'<td><b>{escape(name)}</b>'
               + ('' if crag['profile']['aspect'] else ' <span class="np" title="Wall direction unknown - using average sun exposure. Add an aspect in crag-profiles.json">⚙️</span>')
               + '</td>']
        for i, c in enumerate(row['cells']):
            wk = ' wk' if check_days[i].weekday() >= 5 else ''
            if not c:
                tds.append(f'<td class="na{wk}" data-sort="-1">–</td>')
                continue
            cls, emoji, label = status(c['score'])
            warn = ''.join(f'<div class="warn">⚠️ {escape(w)}</div>' for w in c['warn'])
            tds.append(f'<td class="{cls}{wk}" data-sort="{c["score"]}" title="{escape(c["why"])}">'
                       f'{emoji} <b>{c["score"]}</b><div class="why">{escape(c["why"])}</div>{warn}</td>')
        dist = crag.get('Distance', 0)
        tds.append(f'<td data-sort="{row["rain72"]:.1f}">{row["rain72"]:.0f} mm</td>')
        tds.append(f'<td data-sort="{dist}">{fmt_drive(dist)}</td>')
        tds.append(f'<td><a href="https://plezanje.net/plezalisce/{slug}" target="_blank">plezanje.net</a> · '
                   f'<a href="https://www.thecrag.com/en/climbing/world/search?only=areas&S={escape(name)}" target="_blank">theCrag</a> · '
                   f'<a href="https://www.yr.no/en/forecast/daily-table/{str(lat)[:6]}, {str(lon)[:6]}" target="_blank">Yr</a> · '
                   f'<a href="https://www.google.com/maps/place/{str(park[0])[:6]},{str(park[1])[:6]}" target="_blank">Maps</a></td>')
        body.append(f'<tr type="{crag.get("type", "")}" data-dist="{dist}">' + ''.join(tds) + '</tr>')

    if best:
        _, bname, bday = best
        headline = f'Driest this weekend: <span class="top-pick">{escape(bname)}</span> ({DAYS[bday.weekday()]})'
    else:
        headline = 'Is the rock dry?'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Is it dry? - Crag Weather</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{ width:100%; max-width:100%; overflow-x:hidden; }}
body {{ font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       margin:0; padding:14px 16px; background:#fafafa; color:#263238; }}
.header-card {{ background:#fff; border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,.15); padding:16px 20px; margin-bottom:14px; }}
.header-card h1 {{ margin:0 0 8px; font-size:1.4rem; }}
.top-pick {{ color:#37474f; border-bottom:3px solid #37474f; }}
.header-card p {{ margin:0; color:#555; font-size:.9rem; line-height:1.6; }}
.controls {{ display:flex; flex-wrap:wrap; gap:14px; align-items:center; margin-top:12px; font-size:.9rem; }}
.controls select, .controls input {{ font-size:.9rem; }}
.controls input[type=checkbox] {{ width:18px; height:18px; vertical-align:middle; }}
.feature-btn {{ display:inline-block; margin-top:12px; padding:8px 14px; background:#37474f; color:#fff;
               text-decoration:none; border-radius:6px; font-size:.85rem; }}
details {{ margin-top:12px; font-size:.85rem; color:#555; }}
details li {{ margin:3px 0; }}
.table-wrapper {{ width:100%; max-height:75vh; overflow:auto; -webkit-overflow-scrolling:touch; margin:10px 0;
                 border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,.2); }}
.myTable {{ background:#f7f7f7; border-collapse:collapse; font-size:14px; white-space:nowrap; }}
.myTable td, .myTable th {{ padding:8px 10px; border:1px solid #ddd; vertical-align:top; }}
.myTable th {{ position:sticky; top:0; z-index:2; background:#37474f; color:#fff; border-color:#263238; cursor:pointer; user-select:none; }}
.myTable th.wk {{ background:#263238; }}
.myTable td:first-child, .myTable th:first-child {{ position:sticky; left:0; z-index:1; background:#f7f7f7; }}
.myTable th:first-child {{ z-index:3; background:#37474f; }}
td.dry  {{ background:#e3f4e1; }}
td.damp {{ background:#fff6d6; }}
td.wet  {{ background:#dbe9f7; }}
td.wk   {{ box-shadow:inset 0 0 0 2px #90a4ae; }}
td.na   {{ color:#999; }}
.why {{ font-size:11px; color:#607d8b; white-space:normal; min-width:110px; max-width:150px; line-height:1.3; margin-top:2px; }}
.warn {{ font-size:11px; color:#b45309; white-space:normal; }}
.np {{ font-size:.7em; cursor:help; }}
.legend {{ font-size:.8rem; color:#555; margin-top:6px; }}
</style>
<script>
let sortCol = null, sortAsc = false;
function sortTable(c) {{
  const t = document.getElementById('dryTable'), tb = t.tBodies[0] || t;
  sortAsc = (sortCol === c) ? !sortAsc : (c > {n});
  sortCol = c;
  const rows = Array.from(tb.rows).slice(1);
  rows.sort((a, b) => {{
    const ra = a.cells[c].getAttribute('data-sort'), rb = b.cells[c].getAttribute('data-sort');
    const na = ra !== null ? parseFloat(ra) : NaN, nb = rb !== null ? parseFloat(rb) : NaN;
    const cmp = (!isNaN(na) && !isNaN(nb)) ? na - nb : a.cells[c].textContent.trim().localeCompare(b.cells[c].textContent.trim());
    return sortAsc ? cmp : -cmp;
  }});
  rows.forEach(r => tb.appendChild(r));
}}
function filterRows() {{
  const maxD = parseFloat(document.getElementById('maxDrive').value);
  const mp = document.getElementById('mpOnly').checked;
  const dryOnly = document.getElementById('dryOnly').checked;
  const rows = document.getElementById('dryTable').rows;
  for (let i = 1; i < rows.length; i++) {{
    const r = rows[i];
    let show = parseFloat(r.getAttribute('data-dist')) <= maxD;
    if (mp && r.getAttribute('type') !== 'multipitch') show = false;
    if (dryOnly && !Array.from(r.cells).some(td => td.classList.contains('dry') && td.classList.contains('wk'))) show = false;
    r.style.display = show ? '' : 'none';
  }}
}}
</script>
</head>
<body>
<div class="header-card">
  <h1>{headline}</h1>
  <p>Estimated rock dryness at {CHECK_HOUR}:00 each day, 0 (soaked) to 100 (bone dry).<br>
     Updated on {updated} · {escape(source_note)}</p>
  <div class="controls">
    <label>Max drive
      <select id="maxDrive" onchange="filterRows()">
        <option value="60">1h</option><option value="120">2h</option>
        <option value="180">3h</option><option value="99999" selected>any</option>
      </select></label>
    <label><input type="checkbox" id="dryOnly" onchange="filterRows()"> Dry at the weekend</label>
    <label><input type="checkbox" id="mpOnly" onchange="filterRows()"> Multi-pitch only</label>
  </div>
  <details>
    <summary>How the dryness score works</summary>
    <ul>
      <li>Runs an hour-by-hour water balance on the wall over the last {PAST_DAYS} days and the next {FORECAST_DAYS}.</li>
      <li><b>Wetter:</b> rain (only ~20% reaches steep/sheltered walls), and condensation when the air sits at the dew point with no sun.</li>
      <li><b>Drier:</b> dry air (vapour-pressure deficit), wind, and sunshine on the wall's aspect at that time of day (east walls dry in the morning, west in the afternoon, north barely).</li>
      <li>Rock type changes the speed (granite/gneiss faster, conglomerate/sandstone slower). Crags with ⚙️ have no known wall direction and use an average sun exposure. Rock is limestone unless set otherwise.</li>
      <li>✅ 75+ dry · 🟡 40-74 damp · 💧 under 40 wet. It's a model - seepage, cracks and local showers can still surprise you.</li>
    </ul>
  </details>
  <a class="feature-btn" href="index.html">← Crag weather</a>
  <a class="feature-btn" href="https://github.com/paitty/crag-weather/issues/new?title=Dryness+report%3A+&labels=dryness" target="_blank">📝 Report real conditions</a>
</div>
<div class="table-wrapper">
<table class="myTable" id="dryTable">
<tr><th onclick="sortTable(0)">Crag</th>{head_days}
<th onclick="sortTable({n+1})">Rain 72h</th><th onclick="sortTable({n+2})">Distance</th><th>Links</th></tr>
{chr(10).join(body)}
</table>
</div>
<p class="legend">Weekend days are outlined. Tap a column header to sort. Weather: Open-Meteo.</p>
</body>
</html>
"""


def main():
    sample = '--sample' in sys.argv
    crags = load_crags()
    if sample:
        weather, note = sample_weather(crags), 'SAMPLE DATA - not a real forecast'
    else:
        weather, note = fetch_weather(crags), 'Based on Open-Meteo'
    check_days, rows = build_rows(crags, weather)
    html = render(check_days, rows, note)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[dryness] wrote {OUTPUT_FILE} with {len(rows)} crags')


if __name__ == '__main__':
    main()
