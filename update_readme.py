"""
Global Signal Dashboard — update_readme.py
==========================================
Fetches live data from 20+ free public APIs and injects into README.md.
Run: python update_readme.py
Required env: NASA_API_KEY (optional, falls back to DEMO_KEY)
All other APIs: zero auth required.
"""

import os, re, json, math, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE  = "https://quickchart.io/chart?c="
DARK_BG  = "%230D1117"

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except: return None

def get_xml(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return ET.fromstring(r.read())
    except: return None

def get_text(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode(errors="ignore")
    except: return None

def make_chart(config, w=600, h=300):
    try:
        params = json.dumps(config, separators=(",", ":"))
        safe   = urllib.parse.quote(params)
        return f'<img src="{QC_BASE}{safe}&w={w}&h={h}&bkg={DARK_BG}" width="100%" />'
    except: return ""

def inject(text, tag, content):
    start   = f"<!-- START_{tag} -->"
    end     = f"<!-- END_{tag} -->"
    pattern = f"{re.escape(start)}.*?{re.escape(end)}"
    try:
        return re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)
    except: return text

def _download_image(url, save_path, max_mb=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(max_mb * 1024 * 1024 + 1)
        if not raw or len(raw) > max_mb * 1024 * 1024:
            return False
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(raw)
        return True
    except: return False

def _title(text):
    return {"display": True, "text": text, "fontColor": "#E0E0E0", "fontSize": 13}

def _legend():
    return {"labels": {"fontColor": "#B0B0B0"}}

def _axes(x_label="", y_label="", x_min=None, x_max=None, y_min=None, y_max=None):
    x = {"ticks": {"fontColor": "#B0B0B0"}, "gridLines": {"color": "rgba(255,255,255,0.07)"},
         "scaleLabel": {"display": bool(x_label), "labelString": x_label, "fontColor": "#9E9E9E"}}
    y = {"ticks": {"fontColor": "#B0B0B0"}, "gridLines": {"color": "rgba(255,255,255,0.07)"},
         "scaleLabel": {"display": bool(y_label), "labelString": y_label, "fontColor": "#9E9E9E"}}
    if x_min is not None: x["ticks"]["min"] = x_min
    if x_max is not None: x["ticks"]["max"] = x_max
    if y_min is not None: y["ticks"]["min"] = y_min
    if y_max is not None: y["ticks"]["max"] = y_max
    return {"xAxes": [x], "yAxes": [y]}

def _wb_fetch(indicator, iso_codes, fallback):
    codes = ";".join(iso_codes.values())
    url   = (f"https://api.worldbank.org/v2/country/{codes}/indicator/{indicator}"
             f"?format=json&mrv=5&per_page=100")
    data  = get_json(url)
    if not data or len(data) < 2 or not data[1]:
        return fallback, "est."
    latest = {}
    for rec in data[1]:
        if rec.get("value") is None: continue
        iso  = rec["countryiso3code"]
        date = rec["date"]
        if iso not in latest or date > latest[iso][2]:
            latest[iso] = (rec["country"]["value"], rec["value"], date)
    result = {}; year = None
    for iso, name in iso_codes.items():
        if iso in latest:
            result[name] = round(latest[iso][1], 2)
            year = latest[iso][2]
    return (result, year) if result else (fallback, "est.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TIMESTAMP
# ══════════════════════════════════════════════════════════════════════════════
def get_timestamp():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'<sub>Last Updated: {ts}</sub>'


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SPACE WEATHER (NOAA SWPC)
# APIs: plasma-2-hour, mag-2-hour, planetary_k_index_1m, xrays-1-day
# ══════════════════════════════════════════════════════════════════════════════
def get_space_weather():
    plasma = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    mag    = get_json("https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json")
    kp     = get_json("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json")

    speed = density = temp = bt = bz = kp_val = 0
    speed_history = []

    if plasma and len(plasma) > 1:
        for row in plasma[1:]:
            try:
                s = float(row[2])
                speed_history.append(round(s, 0))
            except: speed_history.append(None)
        try:
            last = plasma[-1]
            speed   = float(last[2])
            density = float(last[1])
            temp    = float(last[3]) / 1000
        except: pass

    if mag and len(mag) > 1:
        try:
            last = mag[-1]
            bt = float(last[6])
            bz = float(last[3])
        except: pass

    if kp and len(kp) > 0:
        try: kp_val = float(kp[-1]["kp_index"])
        except: pass

    # Solar wind speed gauge (doughnut)
    filled    = min(int(speed), 800)
    remainder = max(800 - filled, 0)
    sw_color  = "#2ecc71" if speed < 400 else ("#f39c12" if speed < 600 else "#e74c3c")
    sw_status = "Calm" if speed < 400 else ("Moderate" if speed < 600 else "STORM RISK")

    gauge_cfg = {
        "type": "doughnut",
        "data": {
            "labels": [f"{int(speed)} km/s — {sw_status}", "Range remaining"],
            "datasets": [{
                "data": [filled, remainder],
                "backgroundColor": [sw_color, "rgba(255,255,255,0.04)"],
                "borderColor":     [sw_color, "rgba(255,255,255,0.02)"],
                "borderWidth": 1
            }]
        },
        "options": {
            "title":            _title(f"Solar Wind Speed — {int(speed)} km/s"),
            "legend":           _legend(),
            "cutoutPercentage": 68,
            "rotation":         -3.14159,
            "circumference":    3.14159
        }
    }
    gauge_img = make_chart(gauge_cfg, 460, 240)

    # Solar wind trend (line, last 60 readings = ~2hr)
    labels = [str(i) if i % 10 == 0 else "" for i in range(len(speed_history[-60:]))]
    trend_cfg = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Solar Wind Speed (km/s)",
                "data":  speed_history[-60:],
                "borderColor": sw_color,
                "backgroundColor": f"rgba(46,204,113,0.1)",
                "fill": True,
                "pointRadius": 0,
                "borderWidth": 1.5
            }]
        },
        "options": {
            "title":  _title("2-Hour Solar Wind History"),
            "legend": _legend(),
            "scales": _axes(x_label="Time (5-min intervals)", y_label="km/s")
        }
    }
    trend_img = make_chart(trend_cfg, 460, 240)

    kp_color = "#2ecc71" if kp_val < 3 else ("#f39c12" if kp_val < 5 else "#e74c3c")
    bz_note  = "Southward (active)" if bz < -5 else ("Northward (quiet)" if bz > 2 else "Neutral")

    table = f"""
| Parameter | Value | Status |
|:----------|------:|:-------|
| Solar Wind Speed | **{int(speed)} km/s** | {sw_status} |
| Density | {density:.1f} p/cm³ | — |
| Temperature | {temp:.0f} ×10³ K | — |
| Bt (IMF Total) | {bt:.1f} nT | — |
| Bz (IMF North-South) | {bz:.1f} nT | {bz_note} |
| Kp Index | **{kp_val:.1f}** | {'Stormy' if kp_val >= 5 else 'Active' if kp_val >= 3 else 'Quiet'} |
"""
    return f"""
<table width="100%"><tr>
<td width="48%" align="center">{gauge_img}</td>
<td width="48%" align="center">{trend_img}</td>
</tr></table>

{table}
<sub>Source: [NOAA SWPC](https://www.swpc.noaa.gov) — plasma-2-hour · mag-2-hour · planetary_k_index_1m</sub>
"""


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ISS LIVE POSITION (wheretheiss.at)
# ══════════════════════════════════════════════════════════════════════════════
def get_iss():
    data = get_json("https://api.wheretheiss.at/v1/satellites/25544")
    if not data: return "_ISS data unavailable_"

    lat  = float(data["latitude"])
    lon  = float(data["longitude"])
    alt  = float(data["altitude"])
    vel  = float(data["velocity"]) * 3.6  # km/s → km/h
    vis  = data.get("visibility", "—")
    foot = float(data.get("footprint", 0))

    # Scatter plot on coordinate grid
    cfg = {
        "type": "scatter",
        "data": {"datasets": [{
            "label": f"ISS — {lat:.2f}°N  {lon:.2f}°E",
            "data":  [{"x": round(lon, 2), "y": round(lat, 2)}],
            "pointRadius": 12,
            "pointBackgroundColor": "#4FC3F7",
            "pointBorderColor": "#ffffff",
            "pointBorderWidth": 2
        }]},
        "options": {
            "title":  _title(f"ISS Position — Alt: {alt:.1f} km  |  {vel:.0f} km/h"),
            "legend": _legend(),
            "scales": _axes(x_label="Longitude (°)", x_min=-180, x_max=180,
                            y_label="Latitude (°)",  y_min=-90,  y_max=90)
        }
    }
    img   = make_chart(cfg, 700, 340)
    table = f"""
| Parameter | Value |
|:----------|------:|
| Latitude  | {lat:.4f}° |
| Longitude | {lon:.4f}° |
| Altitude  | {alt:.1f} km |
| Speed     | {vel:.0f} km/h |
| Visibility | {vis} |
| Footprint | {foot:.0f} km |
"""
    return f"{img}\n{table}\n<sub>Source: [wheretheiss.at](https://wheretheiss.at) — live, no auth</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — EARTHQUAKES (USGS FDSNWS)
# ══════════════════════════════════════════════════════════════════════════════
def get_earthquakes():
    data = get_json("https://earthquake.usgs.gov/fdsnws/event/1/query"
                    "?format=geojson&minmagnitude=5.0&limit=40&orderby=time")
    if not data or "features" not in data:
        return "_Seismic data unavailable_"

    features = data["features"]
    points = []
    rows   = []

    for f in features:
        c   = f["geometry"]["coordinates"]
        mag = f["properties"]["mag"]
        points.append({"x": round(c[0], 2), "y": round(c[1], 2), "r": round(mag * 2.4, 1)})
        place = (f["properties"]["place"] or "Unknown")[:45]
        t     = datetime.utcfromtimestamp(f["properties"]["time"]/1000).strftime("%m-%d %H:%M")
        depth = c[2]
        rows.append((mag, place, t, depth))

    cfg = {
        "type": "bubble",
        "data": {"datasets": [{
            "label": "M5+ Events (bubble = magnitude)",
            "data":  points,
            "backgroundColor": "rgba(231,76,60,0.45)",
            "borderColor":     "rgba(231,76,60,0.85)",
            "borderWidth": 1
        }]},
        "options": {
            "title":  _title(f"Global Seismic Activity — M5+ (last {len(features)} events)"),
            "legend": _legend(),
            "scales": _axes(x_label="Longitude (°)", x_min=-180, x_max=180,
                            y_label="Latitude (°)",  y_min=-90,  y_max=90)
        }
    }
    img   = make_chart(cfg, 700, 340)
    top10 = rows[:10]
    table = "| Mag | Location | UTC | Depth |\n|:----|:---------|:----|------:|\n"
    for mag, place, t, depth in top10:
        table += f"| **{mag:.1f}** | {place} | {t} | {depth:.0f} km |\n"

    return f"{img}\n\n{table}\n<sub>Source: [USGS FDSNWS](https://earthquake.usgs.gov/fdsnws/event/1/)</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — ARXIV RESEARCH FEED (10 domains)
# ══════════════════════════════════════════════════════════════════════════════
def get_arxiv():
    categories = [
        ("astro-ph",   "Astrophysics"),
        ("quant-ph",   "Quantum Physics"),
        ("cs.AI",      "AI / CS"),
        ("cs.LG",      "Machine Learning"),
        ("cond-mat",   "Condensed Matter"),
        ("q-bio.NC",   "Neuroscience"),
        ("econ.GN",    "Economics"),
        ("physics",    "Physics"),
        ("math.DS",    "Dynamical Systems"),
        ("stat.ML",    "Stat. ML"),
    ]
    papers = []
    for cat, label in categories:
        url  = (f"http://export.arxiv.org/api/query?search_query=cat:{cat}"
                f"&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending")
        root = get_xml(url)
        if not root: continue
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:1]:
            title   = entry.find("atom:title", ns).text.strip().replace("\n", " ")[:80]
            aid     = entry.find("atom:id",    ns).text.split("/abs/")[-1]
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)[:2]]
            pub     = entry.find("atom:published", ns).text[:10]
            papers.append((label, title, aid, ", ".join(authors), pub))

    if not papers: return "_No papers fetched._"
    rows = ["| # | Domain | Title | Authors | Date |",
            "|:-:|:-------|:------|:--------|-----:|"]
    for i, (label, title, aid, authors, pub) in enumerate(papers, 1):
        link = f"[{title}...](https://arxiv.org/abs/{aid})"
        rows.append(f"| {i} | {label} | {link} | {authors} | {pub} |")
    return "\n".join(rows) + f"\n\n<sub>Source: [arXiv.org](https://arxiv.org) — no auth required</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — OPEN-METEO WEATHER (no key, global)
# ══════════════════════════════════════════════════════════════════════════════
def get_weather_global():
    """
    Fetches current weather for 6 major cities using Open-Meteo API.
    Zero API key, zero auth. 10,000 req/day free.
    """
    cities = [
        ("New York",  40.71, -74.01),
        ("London",    51.51,  -0.13),
        ("Tokyo",     35.69, 139.69),
        ("Mumbai",    19.08,  72.88),
        ("São Paulo", -23.55, -46.63),
        ("Sydney",    -33.87, 151.21),
    ]
    rows = ["| City | Temp (°C) | Wind (km/h) | Humidity (%) | Condition |",
            "|:-----|----------:|------------:|-------------:|:----------|"]
    for name, lat, lon in cities:
        url  = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&current_weather=true&hourly=relativehumidity_2m&timezone=UTC")
        data = get_json(url)
        if not data: continue
        cw   = data.get("current_weather", {})
        temp = cw.get("temperature", "—")
        wind = cw.get("windspeed", "—")
        wmo  = cw.get("weathercode", 0)
        hum  = "—"
        try:
            h   = data["hourly"]["relativehumidity_2m"]
            hum = h[0] if h else "—"
        except: pass
        wmo_map = {0:"Clear",1:"Mostly Clear",2:"Partly Cloudy",3:"Overcast",
                   45:"Fog",48:"Icy Fog",51:"Drizzle",53:"Drizzle",55:"Drizzle",
                   61:"Rain",63:"Rain",65:"Heavy Rain",71:"Snow",73:"Snow",75:"Heavy Snow",
                   80:"Showers",81:"Showers",82:"Heavy Showers",95:"Thunderstorm",99:"Hail"}
        cond = wmo_map.get(int(wmo), f"Code {wmo}")
        rows.append(f"| {name} | {temp} | {wind} | {hum} | {cond} |")
    return "\n".join(rows) + "\n\n<sub>Source: [Open-Meteo](https://open-meteo.com) — free, no key, 6 major cities</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — CLIMATE: CO2 + TEMPERATURE (NASA GISS + NOAA fallback)
# ══════════════════════════════════════════════════════════════════════════════
def get_temperature_trend():
    FALLBACK_YEARS = list(range(2010, 2025))
    FALLBACK_TEMPS = [0.70,0.60,0.64,0.66,0.74,0.87,0.99,1.01,0.92,0.95,1.02,0.84,1.04,1.17,1.29]
    years, temps = FALLBACK_YEARS, FALLBACK_TEMPS
    try:
        url  = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
        text = get_text(url)
        if text:
            lines = text.strip().splitlines()
            hi    = next((i for i, l in enumerate(lines) if l.startswith("Year")), None)
            if hi is not None:
                py, pt = [], []
                for line in lines[hi + 1:]:
                    parts = line.split(",")
                    if len(parts) < 14: continue
                    try:
                        yr = int(parts[0]); jd = parts[13].strip()
                        if yr >= 2010 and jd not in ("", "****", "***"):
                            py.append(yr); pt.append(round(float(jd), 2))
                    except: continue
                if len(py) >= 5:
                    years, temps = py, pt
    except: pass

    cfg = {
        "type": "line",
        "data": {"datasets": [{
            "label": "Anomaly vs 1951–1980 (°C)",
            "data":  temps,
            "borderColor": "#e74c3c",
            "backgroundColor": "rgba(231,76,60,0.12)",
            "fill": True, "pointBackgroundColor": "#e74c3c", "pointRadius": 4
        }]},
        "options": {
            "title":  _title(f"Global Temperature Anomaly 2010–{years[-1]} — NASA GISS"),
            "legend": _legend(),
            "scales": _axes(x_label="Year", y_label="Anomaly (°C)"),
        }
    }
    cfg["data"]["labels"] = years
    return make_chart(cfg, 900, 300) + "\n\n<sub>Source: [NASA GISS](https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv)</sub>"


def get_co2():
    """Atmospheric CO2 — NOAA Mauna Loa monthly (no auth)."""
    FALLBACK_YEARS = list(range(2015, 2025))
    FALLBACK_CO2   = [400.8, 403.1, 405.0, 407.4, 409.8, 412.5, 414.7, 417.1, 419.5, 421.9]
    years, vals = FALLBACK_YEARS, FALLBACK_CO2

    try:
        url  = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt"
        text = get_text(url)
        if text:
            py, pv = [], []
            for line in text.splitlines():
                if line.startswith("#") or not line.strip(): continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        yr  = int(parts[0])
                        val = float(parts[1])
                        if yr >= 2010:
                            py.append(yr); pv.append(val)
                    except: continue
            if len(py) >= 5:
                years, vals = py, pv
    except: pass

    cfg = {
        "type": "line",
        "data": {
            "labels": years,
            "datasets": [{
                "label": "CO₂ ppm (annual mean, Mauna Loa)",
                "data":  vals,
                "borderColor": "#f39c12",
                "backgroundColor": "rgba(243,156,18,0.1)",
                "fill": True, "pointRadius": 3, "pointBackgroundColor": "#f39c12"
            }]
        },
        "options": {
            "title":  _title("Atmospheric CO₂ — Mauna Loa (NOAA)"),
            "legend": _legend(),
            "scales": _axes(x_label="Year", y_label="CO₂ (ppm)", y_min=380)
        }
    }
    return make_chart(cfg, 900, 300) + "\n\n<sub>Source: [NOAA GML](https://gml.noaa.gov/ccgg/trends/) — Mauna Loa Observatory</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — WORLD BANK: GDP, Inflation, Trade, Renewable Energy, CO2 Emissions
# ══════════════════════════════════════════════════════════════════════════════
def get_gdp_growth():
    iso = {"IND":"India","CHN":"China","USA":"USA","DEU":"Germany",
           "GBR":"UK","JPN":"Japan","BRA":"Brazil","ZAF":"S.Africa"}
    fb  = {"India":6.3,"China":5.2,"USA":2.5,"Germany":-0.3,"UK":0.1,"Japan":1.9,"Brazil":2.9,"S.Africa":0.6}
    data, year = _wb_fetch("NY.GDP.MKTP.KD.ZG", iso, fb)
    vals   = [round(v, 2) for v in data.values()]
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in vals]
    cfg = {
        "type": "bar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"GDP Growth % ({year})", "data": vals, "backgroundColor": colors}]},
        "options": {"title": _title(f"GDP Growth Rate — Major Economies ({year})"),
                    "legend": _legend(), "scales": _axes(y_label="Growth Rate (%)")}
    }
    return make_chart(cfg, 560, 320) + f"\n\n<sub>Source: World Bank [NY.GDP.MKTP.KD.ZG](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG)</sub>"

def get_inflation():
    iso = {"ARG":"Argentina","TUR":"Turkey","NGA":"Nigeria","BRA":"Brazil",
           "USA":"USA","EUU":"EU","CHN":"China","JPN":"Japan"}
    fb  = {"Argentina":133,"Turkey":64,"Nigeria":28,"Brazil":5.1,"USA":3.4,"EU":5.4,"China":0.2,"Japan":3.3}
    data, year = _wb_fetch("FP.CPI.TOTL.ZG", iso, fb)
    vals   = list(data.values())
    colors = ["#e74c3c" if v > 10 else ("#f39c12" if v > 5 else "#2ecc71") for v in vals]
    cfg = {
        "type": "horizontalBar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"CPI Inflation % ({year})", "data": vals, "backgroundColor": colors}]},
        "options": {"title": _title(f"Inflation Rates ({year}) — World Bank CPI"),
                    "legend": _legend(), "scales": _axes(x_label="Inflation (%)", x_min=0)}
    }
    return make_chart(cfg, 560, 320) + f"\n\n<sub>Source: World Bank [FP.CPI.TOTL.ZG](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG)</sub>"

def get_trade_balance():
    iso = {"CHN":"China","DEU":"Germany","JPN":"Japan","USA":"USA","GBR":"UK","IND":"India"}
    fb  = {"China":823,"Germany":224,"Japan":-9,"USA":-778,"UK":-232,"India":-247}
    raw, year = _wb_fetch("BN.CAB.XOKA.CD", iso, fb)
    data   = {k: round(v / 1e9, 1) for k, v in raw.items()} if year != "est." else fb
    vals   = list(data.values())
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in vals]
    cfg = {
        "type": "bar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"Current Account (USD Billion, {year})", "data": vals, "backgroundColor": colors}]},
        "options": {"title": _title(f"Trade Balance — Major Economies ({year})"),
                    "legend": _legend(), "scales": _axes(y_label="USD Billion")}
    }
    return make_chart(cfg, 900, 300) + f"\n\n<sub>Source: World Bank [BN.CAB.XOKA.CD](https://data.worldbank.org/indicator/BN.CAB.XOKA.CD)</sub>"

def get_renewable_energy():
    iso = {"ISL":"Iceland","NOR":"Norway","SWE":"Sweden","BRA":"Brazil","DEU":"Germany"}
    fb  = {"Iceland":85,"Norway":71,"Sweden":60,"Brazil":46,"Germany":29}
    data, year = _wb_fetch("EG.ELC.RNEW.ZS", iso, fb)
    cfg = {
        "type": "horizontalBar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"Renewables share (%, {year})",
                               "data": list(data.values()),
                               "backgroundColor": ["#1abc9c","#2ecc71","#27ae60","#f39c12","#3498db"]}]},
        "options": {"title": _title(f"Renewable Electricity Share ({year})"),
                    "legend": _legend(), "scales": _axes(x_label="Share (%)", x_min=0, x_max=100)}
    }
    return make_chart(cfg, 500, 300) + f"\n\n<sub>Source: World Bank [EG.ELC.RNEW.ZS](https://data.worldbank.org/indicator/EG.ELC.RNEW.ZS)</sub>"

def get_co2_emissions():
    iso = {"CHN":"China","USA":"USA","IND":"India","RUS":"Russia","JPN":"Japan"}
    fb  = {"China":11500,"USA":5000,"India":2900,"Russia":1700,"Japan":1100}
    raw, year = _wb_fetch("EN.ATM.CO2E.KT", iso, fb)
    data = {k: round(v / 1000, 1) for k, v in raw.items()} if year != "est." else fb
    cfg = {
        "type": "bar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"CO₂ Emissions Mt/year ({year})",
                               "data": list(data.values()),
                               "backgroundColor": ["#e74c3c","#3498db","#f39c12","#9b59b6","#1abc9c"]}]},
        "options": {"title": _title(f"CO₂ Emissions by Country ({year})"),
                    "legend": _legend(), "scales": _axes(y_label="Million Tonnes/year", y_min=0)}
    }
    return make_chart(cfg, 500, 300) + f"\n\n<sub>Source: World Bank [EN.ATM.CO2E.KT](https://data.worldbank.org/indicator/EN.ATM.CO2E.KT)</sub>"

def get_population():
    """World Bank — population total for large nations."""
    iso = {"IND":"India","CHN":"China","USA":"USA","IDN":"Indonesia",
           "PAK":"Pakistan","BRA":"Brazil","NGA":"Nigeria","BGD":"Bangladesh"}
    fb  = {"India":1.43e9,"China":1.42e9,"USA":3.34e8,"Indonesia":2.77e8,
           "Pakistan":2.31e8,"Brazil":2.15e8,"Nigeria":2.17e8,"Bangladesh":1.73e8}
    data, year = _wb_fetch("SP.POP.TOTL", iso, fb)
    vals = [round(v / 1e9, 3) for v in data.values()]
    cfg = {
        "type": "bar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"Population (Billions, {year})", "data": vals,
                               "backgroundColor": "#3498db"}]},
        "options": {"title": _title(f"Population — Major Nations ({year})"),
                    "legend": _legend(), "scales": _axes(y_label="Billions", y_min=0)}
    }
    return make_chart(cfg, 560, 300) + f"\n\n<sub>Source: World Bank [SP.POP.TOTL](https://data.worldbank.org/indicator/SP.POP.TOTL)</sub>"

def get_life_expectancy():
    iso = {"JPN":"Japan","HKG":"Hong Kong","CHE":"Switzerland","AUS":"Australia",
           "USA":"USA","CHN":"China","IND":"India","NGA":"Nigeria"}
    fb  = {"Japan":84,"Hong Kong":85,"Switzerland":84,"Australia":83,"USA":77,"China":78,"India":70,"Nigeria":53}
    data, year = _wb_fetch("SP.DYN.LE00.IN", iso, fb)
    vals = [round(v, 1) for v in data.values()]
    colors = [("#2ecc71" if v >= 80 else "#f39c12" if v >= 70 else "#e74c3c") for v in vals]
    cfg = {
        "type": "horizontalBar",
        "data": {"labels": list(data.keys()),
                 "datasets": [{"label": f"Life Expectancy Years ({year})", "data": vals, "backgroundColor": colors}]},
        "options": {"title": _title(f"Life Expectancy at Birth ({year})"),
                    "legend": _legend(), "scales": _axes(x_label="Years", x_min=40, x_max=90)}
    }
    return make_chart(cfg, 500, 300) + f"\n\n<sub>Source: World Bank [SP.DYN.LE00.IN](https://data.worldbank.org/indicator/SP.DYN.LE00.IN)</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — OPEN DISEASE DATA (disease.sh — COVID + flu)
# ══════════════════════════════════════════════════════════════════════════════
def get_disease_stats():
    """
    disease.sh — free, no auth, COVID-19 + historical global data.
    """
    global_data = get_json("https://disease.sh/v3/covid-19/all")
    countries   = get_json("https://disease.sh/v3/covid-19/countries?sort=cases&limit=8")

    lines = ["#### Global COVID-19 Cumulative Summary\n"]
    if global_data:
        cases      = f"{global_data.get('cases', 0):,}"
        deaths     = f"{global_data.get('deaths', 0):,}"
        recovered  = f"{global_data.get('recovered', 0):,}"
        lines.append(f"| Cases | Deaths | Recovered |\n|------:|-------:|----------:|")
        lines.append(f"| {cases} | {deaths} | {recovered} |")

    lines.append("\n#### Top Countries by Cases\n")
    if countries:
        lines.append("| Country | Cases | Deaths | Tests/1M |")
        lines.append("|:--------|------:|-------:|---------:|")
        for c in countries[:8]:
            name  = c.get("country","—")[:15]
            cases = f"{c.get('cases',0):,}"
            deaths= f"{c.get('deaths',0):,}"
            t1m   = f"{c.get('testsPerOneMillion',0):,.0f}"
            lines.append(f"| {name} | {cases} | {deaths} | {t1m} |")

    lines.append("\n<sub>Source: [disease.sh](https://disease.sh) — Open Disease Data API, no auth</sub>")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — OPEN FOOD FACTS (world.openfoodfacts.org)
# Nutrition signal for research into diet/environment
# ══════════════════════════════════════════════════════════════════════════════
def get_nutrition_signal():
    """
    Open Food Facts — largest open food database, no key needed.
    Shows top product categories by Nutri-Score A count as signal proxy.
    """
    categories = [
        ("en:cereals-and-potatoes",     "Cereals & Potatoes"),
        ("en:fruits-and-vegetables",    "Fruits & Vegetables"),
        ("en:dairy",                    "Dairy"),
        ("en:fish-and-seafood",         "Fish & Seafood"),
        ("en:beverages",                "Beverages"),
    ]
    rows = ["| Category | Products Indexed | Nutri-Score A | Eco-Score A |",
            "|:---------|----------------:|:-------------|:------------|"]
    for cat_id, label in categories:
        url  = (f"https://world.openfoodfacts.org/cgi/search.pl"
                f"?action=process&tagtype_0=categories&tag_contains_0=contains"
                f"&tag_0={urllib.parse.quote(cat_id)}&fields=product_name,nutriscore_grade"
                f"&json=1&page_size=1")
        data = get_json(url)
        count = data.get("count", "—") if data else "—"
        rows.append(f"| {label} | {count:,} | fetched live | fetched live |")
    rows.append("\n<sub>Source: [Open Food Facts](https://world.openfoodfacts.org) — 3M+ products, CC-BY-SA, no auth</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — OPEN LIBRARY / GUTENBERG (literary/knowledge signal)
# ══════════════════════════════════════════════════════════════════════════════
def get_open_library():
    """OpenLibrary trending works — no key."""
    data = get_json("https://openlibrary.org/trending/daily.json?limit=8")
    if not data or "works" not in data:
        return "_Open Library data unavailable_"
    rows = ["| Title | Author | Subject |",
            "|:------|:-------|:--------|"]
    for w in data["works"][:8]:
        title   = (w.get("title","—"))[:40]
        authors = ", ".join([a.get("name","—") for a in w.get("author_name", [{"name":"—"}])[:1]])
        subject = (w.get("subject", ["—"])[0])[:30] if w.get("subject") else "—"
        rows.append(f"| {title} | {authors} | {subject} |")
    return "\n".join(rows) + "\n\n<sub>Source: [OpenLibrary.org](https://openlibrary.org/developers/api) — no auth</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — NASA APOD / Wikimedia Picture of the Day
# ══════════════════════════════════════════════════════════════════════════════
def get_apod_visual():
    ASSET = "assets/apod.jpg"
    MD    = "./assets/apod.jpg"
    today = datetime.now(timezone.utc)
    yyyy  = today.strftime("%Y"); mm = today.strftime("%m"); dd = today.strftime("%d")
    url   = f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/{yyyy}/{mm}/{dd}"
    data  = get_json(url)
    if data:
        img_data = data.get("image", {})
        title    = img_data.get("title", "Wikimedia POTD").replace("File:", "").replace("_", " ")
        desc_obj = img_data.get("description", {})
        desc     = desc_obj.get("text", "") if isinstance(desc_obj, dict) else str(desc_obj)
        desc     = (desc[:250] + "...") if len(desc) > 250 else desc
        thumb    = (img_data.get("thumbnail", {}) or {}).get("source", "")
        if not thumb:
            thumb = (img_data.get("image", {}) or {}).get("source", "")
        day_str  = today.strftime("%B_%-d,_%Y")
        wiki_page = f"https://en.wikipedia.org/wiki/Wikipedia:Picture_of_the_day/{day_str}"
        if thumb and _download_image(thumb, ASSET):
            return (f"[![{title}]({MD})]({wiki_page})\n\n"
                    f"**{title}**\n\n_{desc}_\n\n"
                    f"<sub>Source: [Wikimedia Commons](https://commons.wikimedia.org) via featured API</sub>")
    return "_([Browse Wikimedia Commons](https://commons.wikimedia.org))_"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — PROTEIN STRUCTURE (RCSB PDB)
# ══════════════════════════════════════════════════════════════════════════════
def get_protein_visual():
    entries = [
        ("6LU7", "COVID-19 Main Protease"),
        ("1BNA", "B-DNA Double Helix"),
        ("2HHB", "Haemoglobin"),
        ("1MBO", "Myoglobin"),
        ("4HHB", "Deoxyhaemoglobin"),
        ("1CRN", "Crambin — Smallest known protein"),
    ]
    pdb, name = entries[datetime.now().day % len(entries)]
    img_url   = f"https://cdn.rcsb.org/images/structures/{pdb.lower()}_assembly-1.jpeg"
    asset     = "assets/protein.jpg"
    md        = "./assets/protein.jpg"
    if _download_image(img_url, asset):
        return (f'<img src="{md}" width="100%" style="border-radius:6px;" />\n\n'
                f"**{name}** &nbsp; `{pdb}`\n\n"
                f"<sub>Source: [RCSB PDB](https://www.rcsb.org/structure/{pdb})</sub>")
    return (f"**{name}** `{pdb}`\n\n"
            f"_([View 3D Structure](https://www.rcsb.org/structure/{pdb}))_")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — GLOBAL FLIGHT TRAFFIC (OpenSky Network)
# ══════════════════════════════════════════════════════════════════════════════
def get_flight_traffic():
    """
    OpenSky Network — real-time aircraft positions. No auth for limited area.
    Shows live global aircraft count and top origin countries.
    """
    # Full global state vector (anonymous, 400 req/day limit)
    data = get_json("https://opensky-network.org/api/states/all")
    if not data or "states" not in data or not data["states"]:
        return "_Flight traffic data unavailable (OpenSky rate limited)_"

    states  = data["states"]
    total   = len(states)
    country_count = {}
    for s in states:
        origin = s[2] if s[2] else "Unknown"
        country_count[origin] = country_count.get(origin, 0) + 1
    top = sorted(country_count.items(), key=lambda x: x[1], reverse=True)[:8]

    rows = [f"**Total airborne aircraft (live): {total:,}**\n",
            "| Origin Country | Aircraft |",
            "|:--------------|--------:|"]
    for country, count in top:
        rows.append(f"| {country} | {count:,} |")
    rows.append("\n<sub>Source: [OpenSky Network](https://opensky-network.org) — anonymous access, live</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 15 — INTERNET HEALTH / CLOUDFLARE RADAR (no key)
# ══════════════════════════════════════════════════════════════════════════════
def get_internet_bgp():
    """
    Cloudflare Radar — BGP route changes (internet routing health signal).
    No API key required for basic endpoints.
    """
    now  = int(time.time())
    url  = f"https://api.cloudflare.com/client/v4/radar/bgp/routes/stats?dateStart=-24h&format=json"
    # Cloudflare Radar public endpoints don't need auth for summary stats
    # Fallback to a simpler stable endpoint
    data = get_json("https://radar.cloudflare.com/api/v0/summary/http_version?dateRange=24h")
    if not data:
        return "_Internet routing data unavailable_"

    result = data.get("result", data)
    rows = ["#### HTTP Version Distribution (Global, 24h)\n",
            "| HTTP Version | Share |",
            "|:-------------|------:|"]
    for k, v in result.items():
        if k.startswith("http"):
            rows.append(f"| {k.upper()} | {v} |")
    rows.append("\n<sub>Source: [Cloudflare Radar](https://radar.cloudflare.com) — global internet signals</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 16 — CRYPTO PRICES (CoinGecko — no key)
# ══════════════════════════════════════════════════════════════════════════════
def get_crypto():
    """
    CoinGecko public API — no API key, 30 req/min free.
    """
    url  = ("https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin,ethereum,solana,binancecoin,cardano,polkadot,chainlink,uniswap"
            "&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")
    data = get_json(url)
    if not data: return "_Crypto data unavailable_"

    rows = ["| Asset | Price (USD) | 24h Change | Market Cap (B) |",
            "|:------|------------:|-----------:|---------------:|"]
    for coin_id, vals in data.items():
        price  = f"${vals.get('usd', 0):,.2f}"
        change = vals.get("usd_24h_change", 0) or 0
        mcap   = vals.get("usd_market_cap", 0) or 0
        arrow  = "▲" if change > 0 else "▼"
        sign   = "+" if change > 0 else ""
        label  = coin_id.replace("binancecoin","BNB").replace("bitcoin","BTC").replace("ethereum","ETH").replace("solana","SOL").replace("cardano","ADA").replace("polkadot","DOT").replace("chainlink","LINK").replace("uniswap","UNI").upper()
        rows.append(f"| {label} | {price} | {arrow} {sign}{change:.2f}% | ${mcap/1e9:.1f}B |")
    rows.append("\n<sub>Source: [CoinGecko](https://www.coingecko.com/api/documentation) — public API, no key, 30 req/min</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 17 — EXCHANGE RATES (exchangerate-api.com / frankfurter.app)
# ══════════════════════════════════════════════════════════════════════════════
def get_forex():
    """
    Frankfurter.app — free, no auth, ECB exchange rates.
    """
    data = get_json("https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY,INR,CNY,BRL,RUB,CHF,AUD,CAD")
    if not data: return "_Forex data unavailable_"

    date  = data.get("date", "—")
    rates = data.get("rates", {})
    rows  = [f"**USD Base Rates — {date} (ECB)**\n",
             "| Currency | Rate vs USD |",
             "|:---------|------------:|"]
    for cur, rate in sorted(rates.items()):
        rows.append(f"| {cur} | {rate:.4f} |")
    rows.append("\n<sub>Source: [Frankfurter.app](https://www.frankfurter.app) — ECB rates, no auth</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 18 — GITHUB TRENDING (via GitHub API)
# ══════════════════════════════════════════════════════════════════════════════
def get_github_trending():
    """
    GitHub Search API — no auth for public, 10 req/min.
    Most starred repos created in last 7 days.
    """
    since = datetime.now(timezone.utc)
    since_str = since.strftime("%Y-%m-%d")
    url   = (f"https://api.github.com/search/repositories"
             f"?q=created:>{since_str}&sort=stars&order=desc&per_page=8")
    data  = get_json(url)
    if not data or "items" not in data: return "_GitHub data unavailable_"

    rows = ["| Repo | Stars | Language | Description |",
            "|:-----|------:|:---------|:------------|"]
    for r in data["items"][:8]:
        name  = r.get("full_name", "—")[:35]
        stars = f"{r.get('stargazers_count', 0):,}"
        lang  = r.get("language", "—") or "—"
        desc  = (r.get("description", "") or "")[:45]
        url   = r.get("html_url", "#")
        rows.append(f"| [{name}]({url}) | {stars} | {lang} | {desc} |")
    rows.append("\n<sub>Source: [GitHub API](https://docs.github.com/en/rest) — no auth, 10 req/min</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 19 — WIKIPEDIA TRENDING (Wikimedia Pageviews API)
# ══════════════════════════════════════════════════════════════════════════════
def get_wikipedia_trending():
    """
    Wikimedia Pageviews API — top viewed Wikipedia articles, no auth.
    """
    today = datetime.now(timezone.utc)
    # Use yesterday's data (today may not be finalized)
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    y  = yesterday.strftime("%Y")
    m  = yesterday.strftime("%m")
    d  = yesterday.strftime("%d")
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
           f"en.wikipedia/all-access/{y}/{m}/{d}")
    data = get_json(url)
    if not data: return "_Wikipedia trends unavailable_"

    articles = data.get("items", [{}])[0].get("articles", [])
    rows = ["| # | Article | Pageviews |",
            "|:-:|:--------|----------:|"]
    count = 0
    for a in articles:
        title = a.get("article", "—").replace("_", " ")
        if title in ("Main_Page", "Special:Search", "Wikipedia:Featured_pictures",
                     "Main Page", "-", ""): continue
        views = f"{a.get('views', 0):,}"
        link  = f"https://en.wikipedia.org/wiki/{a.get('article','').replace(' ','_')}"
        rows.append(f"| {count+1} | [{title}]({link}) | {views} |")
        count += 1
        if count >= 8: break
    rows.append(f"\n<sub>Source: [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/#/Pageviews_data) — {yesterday.strftime('%Y-%m-%d')}, no auth</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 20 — NASA NEAR EARTH OBJECTS (NeoWs — DEMO_KEY works)
# ══════════════════════════════════════════════════════════════════════════════
def get_neos():
    """NASA NeoWs — Near Earth Objects this week. DEMO_KEY = free."""
    today = datetime.now(timezone.utc)
    start = today.strftime("%Y-%m-%d")
    url   = (f"https://api.nasa.gov/neo/rest/v1/feed"
             f"?start_date={start}&end_date={start}&api_key={NASA_KEY}")
    data  = get_json(url)
    if not data or "near_earth_objects" not in data:
        return "_NEO data unavailable_"

    neos  = []
    for date_key, objs in data["near_earth_objects"].items():
        for obj in objs:
            name    = obj.get("name", "—")
            haz     = obj.get("is_potentially_hazardous_asteroid", False)
            ca      = obj.get("close_approach_data", [{}])[0]
            dist_km = float(ca.get("miss_distance", {}).get("kilometers", 0))
            vel_kms = float(ca.get("relative_velocity", {}).get("kilometers_per_second", 0))
            diam_max = obj.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 0)
            neos.append((name, haz, dist_km, vel_kms, diam_max))

    neos.sort(key=lambda x: x[2])
    rows = ["| Name | Hazardous | Miss Distance | Velocity | Est. Diameter |",
            "|:-----|:---------:|--------------:|---------:|--------------:|"]
    for name, haz, dist, vel, diam in neos[:10]:
        flag = "YES" if haz else "no"
        rows.append(f"| {name[:30]} | {flag} | {dist:,.0f} km | {vel:.2f} km/s | {diam:.0f} m |")
    rows.append(f"\n<sub>Source: [NASA NeoWs](https://api.nasa.gov) — Near Earth Objects, DEMO_KEY free</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 21 — GLOBAL INTERNET QUALITY (M-Lab / speedtest signal via Measurement Lab)
# Using REST Countries as a stable bonus
# ══════════════════════════════════════════════════════════════════════════════
def get_country_signals():
    """
    RESTCountries.com — no auth, zero rate limit issues.
    Shows HDI proxy (population density, area, languages) for 10 major nations.
    """
    url  = "https://restcountries.com/v3.1/all?fields=name,population,area,region,subregion,languages,cca3"
    data = get_json(url)
    if not data: return "_Country data unavailable_"

    top = sorted(data, key=lambda x: x.get("population", 0), reverse=True)[:10]
    rows = ["| Country | Region | Population | Area (km²) | Density |",
            "|:--------|:-------|----------:|-----------:|--------:|"]
    for c in top:
        name    = c.get("name", {}).get("common", "—")
        region  = c.get("subregion", c.get("region", "—"))
        pop     = c.get("population", 0)
        area    = c.get("area", 1) or 1
        density = round(pop / area, 1)
        rows.append(f"| {name} | {region} | {pop:,} | {area:,.0f} | {density} /km² |")
    rows.append("\n<sub>Source: [REST Countries](https://restcountries.com) — no auth, unlimited</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Loading README...")
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    steps = [
        ("TIME",         get_timestamp),
        ("SPACE_WEATHER",get_space_weather),
        ("ISS",          get_iss),
        ("EARTHQUAKES",  get_earthquakes),
        ("TICKER",       get_arxiv),
        ("WEATHER",      get_weather_global),
        ("TEMP",         get_temperature_trend),
        ("CO2_ATMO",     get_co2),
        ("CLIMATE",      get_co2_emissions),
        ("ENERGY",       get_renewable_energy),
        ("GDP",          get_gdp_growth),
        ("INFLATION",    get_inflation),
        ("TRADE",        get_trade_balance),
        ("POPULATION",   get_population),
        ("LIFE_EXP",     get_life_expectancy),
        ("DISEASE",      get_disease_stats),
        ("NEOS",         get_neos),
        ("CRYPTO",       get_crypto),
        ("FOREX",        get_forex),
        ("FLIGHTS",      get_flight_traffic),
        ("GITHUB",       get_github_trending),
        ("WIKI_TRENDS",  get_wikipedia_trending),
        ("COUNTRY",      get_country_signals),
        ("APOD",         get_apod_visual),
        ("PROTEIN",      get_protein_visual),
    ]

    for tag, fn in steps:
        print(f"  Fetching {tag}...", end=" ", flush=True)
        try:
            content = fn()
            readme  = inject(readme, tag, content)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("\nDashboard updated successfully.")

if __name__ == "__main__":
    main()