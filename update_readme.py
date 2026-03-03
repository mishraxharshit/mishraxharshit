"""
Global Satellite Signal Dashboard — update_readme.py
=====================================================
Merged: Global Signal Dashboard + Satellite Intelligence Dashboard
40+ free public APIs → single README.md, auto-updated every 6 hours.

Run: python update_readme.py
Optional env:
  NASA_API_KEY   → api.nasa.gov  (falls back to DEMO_KEY)
  FIRMS_MAP_KEY  → firms.modaps.eosdis.nasa.gov (enables live fire map)
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

# ── SATELLITE ALIASES ─────────────────────────────────────────────────────────
import csv, io
FIRMS_KEY = os.environ.get("FIRMS_MAP_KEY", "")
QC = QC_BASE
BG = DARK_BG
jget = get_json
tget = get_text

def chart(cfg, w=900, h=300):
    return make_chart(cfg, w, h)

save_img = _download_image

def axes(xl="", yl="", xn=None, xx=None, yn=None, yx=None):
    return _axes(x_label=xl, y_label=yl, x_min=xn, x_max=xx, y_min=yn, y_max=yx)

def title_opt(t):
    return {"display": True, "text": t, "fontColor": "#E0E0E0", "fontSize": 13}

legend_opt = {"labels": {"fontColor": "#B0B0B0"}}


# ══════════════════════════════════════════════════════════════════════════════
# TIMESTAMP
# ══════════════════════════════════════════════════════════════════════════════
def get_timestamp():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"<sub>Last Updated: **{ts}**</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# SPACE WEATHER · NOAA SWPC (enhanced: X-ray + proton flux + satellite impact)
# ══════════════════════════════════════════════════════════════════════════════
def get_space_weather():
    plasma = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    mag    = get_json("https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json")
    kpdata = get_json("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json")
    xray   = get_json("https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json")
    proton = get_json("https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json")

    speed = density = temp = bt = bz = kp = xflux = pflux = 0.0
    if plasma and len(plasma) > 1:
        try: speed=float(plasma[-1][2]); density=float(plasma[-1][1]); temp=float(plasma[-1][3])/1000
        except: pass
    if mag and len(mag) > 1:
        try: bt=float(mag[-1][6]); bz=float(mag[-1][3])
        except: pass
    if kpdata:
        try: kp=float(kpdata[-1]["kp_index"])
        except: pass
    if xray and len(xray) > 1:
        try: xflux=float(xray[-1]["flux"])
        except: pass
    if proton and len(proton) > 1:
        try: pflux=float(proton[-1]["flux"])
        except: pass

    def flare_class(f):
        if f >= 1e-4: return "**X-class** — major flare"
        if f >= 1e-5: return "**M-class** — moderate"
        if f >= 1e-6: return "**C-class** — minor"
        return "**A/B-class** — quiet"

    status = "STORM" if kp >= 5 else ("ACTIVE" if kp >= 3 else "QUIET")
    sw_col = "#e74c3c" if kp >= 5 else ("#f39c12" if kp >= 3 else "#2ecc71")

    trend_chart = ""
    if plasma and len(plasma) > 2:
        pts = [None if not r[2] else round(float(r[2]), 0) for r in plasma[1:][-72:]]
        try:
            cfg = {
                "type": "line",
                "data": {"labels": [""]*len(pts),
                         "datasets": [{"label": "Solar Wind Speed km/s", "data": pts,
                                       "borderColor": sw_col,
                                       "backgroundColor": "rgba(79,195,247,0.07)",
                                       "fill": True, "pointRadius": 0, "borderWidth": 1.5}]},
                "options": {"title": title_opt(f"Solar Wind Speed — 6hr History ({speed:.0f} km/s now)"),
                            "legend": legend_opt, "scales": axes(yl="km/s")}
            }
            trend_chart = chart(cfg, 900, 200)
        except: pass

    table = f"""
| Parameter | Value | Satellite Operations Impact |
|:----------|------:|:----------------------------|
| Solar Wind Speed | **{speed:.0f} km/s** | {"Elevated LEO drag" if speed > 500 else "Normal drag"} |
| Solar Wind Density | {density:.1f} p/cm³ | {"High ram pressure" if density > 10 else "Normal"} |
| Temperature | {temp:.0f} ×10³ K | — |
| IMF Bz | **{bz:.1f} nT** | {"Storm driver — southward" if bz < -5 else "Quiet — northward" if bz > 2 else "Neutral"} |
| IMF Bt (total) | {bt:.1f} nT | — |
| Kp Index | **{kp:.1f}** | **{status}** — {"GPS error, radiation belt" if kp >= 4 else "Nominal operations"} |
| X-ray Flux (GOES) | {xflux:.2e} W/m² | {flare_class(xflux)} |
| Proton Flux | {pflux:.2e} pfu | {"Radiation belt enhancement" if pflux > 10 else "Nominal"} |
"""
    return (trend_chart + table +
            "\n<sub>Source: [NOAA SWPC](https://www.swpc.noaa.gov) — no auth</sub>")


# ══════════════════════════════════════════════════════════════════════════════
# ISS LIVE POSITION + CREW · wheretheiss.at + Open Notify
# ══════════════════════════════════════════════════════════════════════════════
def get_iss():
    pos  = get_json("https://api.wheretheiss.at/v1/satellites/25544")
    crew = get_json("http://api.open-notify.org/astros.json")
    out  = []

    if pos:
        lat = float(pos["latitude"]);  lon = float(pos["longitude"])
        alt = float(pos["altitude"]);  vel = float(pos["velocity"])
        vis = pos.get("visibility", "—")
        foot = float(pos.get("footprint", 0))

        cfg = {
            "type": "scatter",
            "data": {"datasets": [{
                "label": f"ISS @ {lat:.2f}°N  {lon:.2f}°E",
                "data":  [{"x": round(lon, 2), "y": round(lat, 2)}],
                "pointRadius": 14, "pointBackgroundColor": "#4FC3F7",
                "pointBorderColor": "#ffffff", "pointBorderWidth": 2
            }]},
            "options": {
                "title":  title_opt(f"ISS Live Position — Alt {alt:.0f} km · {vel:.2f} km/s"),
                "legend": legend_opt,
                "scales": axes("Longitude (°)", "Latitude (°)", -180, 180, -90, 90)
            }
        }
        out.append(chart(cfg, 700, 320))
        out.append(f"""
| Parameter | Value |
|:----------|------:|
| Latitude  | {lat:.4f}° |
| Longitude | {lon:.4f}° |
| Altitude  | {alt:.1f} km |
| Velocity  | {vel:.3f} km/s |
| Visibility | {vis} |
| Footprint  | {foot:.0f} km diameter |
""")
    if crew and crew.get("people"):
        iss_crew = [p["name"] for p in crew["people"] if p.get("craft") == "ISS"]
        out.append(f"**Crew aboard ISS ({len(iss_crew)}):** {' · '.join(iss_crew)}")
        out.append(f"\n_Total humans currently in space: **{crew.get('number', '—')}**_")

    out.append("\n<sub>Sources: [wheretheiss.at](https://wheretheiss.at) · [Open Notify](http://open-notify.org/) — no auth</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# EARTHQUAKES · USGS FDSNWS
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
        rows.append((mag, place, t, c[2]))

    cfg = {
        "type": "bubble",
        "data": {"datasets": [{"label": "M5+ Events (bubble = magnitude)", "data": points,
                                "backgroundColor": "rgba(231,76,60,0.45)",
                                "borderColor": "rgba(231,76,60,0.85)", "borderWidth": 1}]},
        "options": {"title": _title(f"Global Seismic Activity — M5+ (last {len(features)} events)"),
                    "legend": _legend(),
                    "scales": _axes(x_label="Longitude (°)", x_min=-180, x_max=180,
                                    y_label="Latitude (°)",  y_min=-90,  y_max=90)}
    }
    img   = make_chart(cfg, 700, 340)
    table = "| Mag | Location | UTC | Depth |\n|:----|:---------|:----|------:|\n"
    for mag, place, t, depth in rows[:10]:
        table += f"| **{mag:.1f}** | {place} | {t} | {depth:.0f} km |\n"
    return f"{img}\n\n{table}\n<sub>Source: [USGS FDSNWS](https://earthquake.usgs.gov/fdsnws/event/1/)</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# NEAR EARTH OBJECTS · NASA NeoWs (enhanced)
# ══════════════════════════════════════════════════════════════════════════════
def get_neos():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data  = get_json(f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key={NASA_KEY}")
    if not data: return "_NEO data unavailable_"

    neos = []
    for _, objs in data.get("near_earth_objects", {}).items():
        for o in objs:
            ca   = (o.get("close_approach_data") or [{}])[0]
            dist = float(ca.get("miss_distance",{}).get("kilometers",0))
            vel  = float(ca.get("relative_velocity",{}).get("kilometers_per_second",0))
            diam = o.get("estimated_diameter",{}).get("meters",{}).get("estimated_diameter_max",0)
            neos.append((o.get("name","—"), o.get("is_potentially_hazardous_asteroid",False), dist, vel, diam))
    neos.sort(key=lambda x: x[2])

    out  = f"**Today's near-Earth approaches: {len(neos)}**\n\n"
    out += "| Object | Hazardous | Miss Distance | Velocity | Diameter |\n"
    out += "|:-------|:---------:|--------------:|---------:|---------:|\n"
    for name, haz, dist, vel, diam in neos[:10]:
        out += f"| {name[:30]} | {'**YES**' if haz else 'no'} | {dist:,.0f} km | {vel:.2f} km/s | {diam:.0f} m |\n"
    return out + f"\n<sub>Source: [NASA NeoWs](https://api.nasa.gov) — DEMO_KEY</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# WEATHER · Open-Meteo (6 cities, no key)
# ══════════════════════════════════════════════════════════════════════════════
def get_weather_global():
    cities = [("New York",40.71,-74.01),("London",51.51,-0.13),("Tokyo",35.69,139.69),
              ("Mumbai",19.08,72.88),("São Paulo",-23.55,-46.63),("Sydney",-33.87,151.21)]
    rows = ["| City | Temp (°C) | Wind (km/h) | Humidity (%) | Condition |",
            "|:-----|----------:|------------:|-------------:|:----------|"]
    for name, lat, lon in cities:
        url  = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&current_weather=true&hourly=relativehumidity_2m&timezone=UTC")
        data = get_json(url)
        if not data: continue
        cw   = data.get("current_weather", {})
        temp = cw.get("temperature", "—"); wind = cw.get("windspeed", "—")
        wmo  = cw.get("weathercode", 0); hum = "—"
        try: hum = data["hourly"]["relativehumidity_2m"][0]
        except: pass
        wmo_map = {0:"Clear",1:"Mostly Clear",2:"Partly Cloudy",3:"Overcast",45:"Fog",
                   61:"Rain",63:"Rain",65:"Heavy Rain",71:"Snow",80:"Showers",95:"Thunderstorm"}
        rows.append(f"| {name} | {temp} | {wind} | {hum} | {wmo_map.get(int(wmo),f'Code {wmo}')} |")
    return "\n".join(rows) + "\n\n<sub>Source: [Open-Meteo](https://open-meteo.com) — free, no key</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# TEMPERATURE TREND · NASA GISS
# ══════════════════════════════════════════════════════════════════════════════
def get_temperature_trend():
    FALLBACK_YEARS = list(range(2010, 2025))
    FALLBACK_TEMPS = [0.70,0.60,0.64,0.66,0.74,0.87,0.99,1.01,0.92,0.95,1.02,0.84,1.04,1.17,1.29]
    years, temps = FALLBACK_YEARS, FALLBACK_TEMPS
    try:
        text = get_text("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv")
        if text:
            lines = text.strip().splitlines()
            hi = next((i for i, l in enumerate(lines) if l.startswith("Year")), None)
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
                if len(py) >= 5: years, temps = py, pt
    except: pass

    cfg = {"type": "line",
           "data": {"labels": years, "datasets": [{"label": "Anomaly vs 1951–1980 (°C)", "data": temps,
                    "borderColor": "#e74c3c", "backgroundColor": "rgba(231,76,60,0.12)",
                    "fill": True, "pointBackgroundColor": "#e74c3c", "pointRadius": 4}]},
           "options": {"title": _title(f"Global Temperature Anomaly 2010–{years[-1]} — NASA GISS"),
                       "legend": _legend(), "scales": _axes(x_label="Year", y_label="Anomaly (°C)")}}
    return make_chart(cfg, 900, 300) + "\n\n<sub>Source: [NASA GISS](https://data.giss.nasa.gov/gistemp/)</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# CO2 · NOAA Mauna Loa
# ══════════════════════════════════════════════════════════════════════════════
def get_co2():
    years = list(range(2015, 2025))
    vals  = [400.8,403.1,405.0,407.4,409.8,412.5,414.7,417.1,419.5,421.9]
    try:
        text = get_text("https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt")
        if text:
            py, pv = [], []
            for line in text.splitlines():
                if line.startswith("#") or not line.strip(): continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        yr = int(parts[0]); val = float(parts[1])
                        if yr >= 2010: py.append(yr); pv.append(val)
                    except: continue
            if len(py) >= 5: years, vals = py, pv
    except: pass

    cfg = {"type": "line",
           "data": {"labels": years, "datasets": [{"label": "CO₂ ppm (annual mean, Mauna Loa)", "data": vals,
                    "borderColor": "#f39c12", "backgroundColor": "rgba(243,156,18,0.1)",
                    "fill": True, "pointRadius": 3, "pointBackgroundColor": "#f39c12"}]},
           "options": {"title": _title("Atmospheric CO₂ — Mauna Loa (NOAA)"),
                       "legend": _legend(), "scales": _axes(x_label="Year", y_label="CO₂ (ppm)", y_min=380)}}
    return make_chart(cfg, 900, 300) + "\n\n<sub>Source: [NOAA GML](https://gml.noaa.gov/ccgg/trends/)</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# WORLD BANK — GDP, Inflation, Trade, Energy, CO2, Population, Life Expectancy
# ══════════════════════════════════════════════════════════════════════════════
def get_gdp_growth():
    iso = {"IND":"India","CHN":"China","USA":"USA","DEU":"Germany","GBR":"UK","JPN":"Japan","BRA":"Brazil","ZAF":"S.Africa"}
    fb  = {"India":6.3,"China":5.2,"USA":2.5,"Germany":-0.3,"UK":0.1,"Japan":1.9,"Brazil":2.9,"S.Africa":0.6}
    data, year = _wb_fetch("NY.GDP.MKTP.KD.ZG", iso, fb)
    vals = [round(v,2) for v in data.values()]
    cfg = {"type":"bar","data":{"labels":list(data.keys()),"datasets":[{"label":f"GDP Growth % ({year})","data":vals,
           "backgroundColor":["#2ecc71" if v>=0 else "#e74c3c" for v in vals]}]},
           "options":{"title":_title(f"GDP Growth Rate ({year})"),"legend":_legend(),"scales":_axes(y_label="Growth Rate (%)")}}
    return make_chart(cfg,560,320)+f"\n\n<sub>Source: World Bank [NY.GDP.MKTP.KD.ZG](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG)</sub>"

def get_inflation():
    iso = {"ARG":"Argentina","TUR":"Turkey","NGA":"Nigeria","BRA":"Brazil","USA":"USA","EUU":"EU","CHN":"China","JPN":"Japan"}
    fb  = {"Argentina":133,"Turkey":64,"Nigeria":28,"Brazil":5.1,"USA":3.4,"EU":5.4,"China":0.2,"Japan":3.3}
    data, year = _wb_fetch("FP.CPI.TOTL.ZG", iso, fb)
    vals = list(data.values())
    cfg = {"type":"horizontalBar","data":{"labels":list(data.keys()),"datasets":[{"label":f"CPI Inflation % ({year})","data":vals,
           "backgroundColor":["#e74c3c" if v>10 else "#f39c12" if v>5 else "#2ecc71" for v in vals]}]},
           "options":{"title":_title(f"Inflation Rates ({year})"),"legend":_legend(),"scales":_axes(x_label="Inflation (%)",x_min=0)}}
    return make_chart(cfg,560,320)+f"\n\n<sub>Source: World Bank [FP.CPI.TOTL.ZG](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG)</sub>"

def get_trade_balance():
    iso = {"CHN":"China","DEU":"Germany","JPN":"Japan","USA":"USA","GBR":"UK","IND":"India"}
    fb  = {"China":823,"Germany":224,"Japan":-9,"USA":-778,"UK":-232,"India":-247}
    raw, year = _wb_fetch("BN.CAB.XOKA.CD", iso, fb)
    data = {k:round(v/1e9,1) for k,v in raw.items()} if year!="est." else fb
    vals = list(data.values())
    cfg = {"type":"bar","data":{"labels":list(data.keys()),"datasets":[{"label":f"Current Account USD Billion ({year})","data":vals,
           "backgroundColor":["#2ecc71" if v>=0 else "#e74c3c" for v in vals]}]},
           "options":{"title":_title(f"Trade Balance ({year})"),"legend":_legend(),"scales":_axes(y_label="USD Billion")}}
    return make_chart(cfg,900,300)+f"\n\n<sub>Source: World Bank [BN.CAB.XOKA.CD](https://data.worldbank.org/indicator/BN.CAB.XOKA.CD)</sub>"

def get_renewable_energy():
    iso = {"ISL":"Iceland","NOR":"Norway","SWE":"Sweden","BRA":"Brazil","DEU":"Germany"}
    fb  = {"Iceland":85,"Norway":71,"Sweden":60,"Brazil":46,"Germany":29}
    data, year = _wb_fetch("EG.ELC.RNEW.ZS", iso, fb)
    cfg = {"type":"horizontalBar","data":{"labels":list(data.keys()),"datasets":[{"label":f"Renewables % ({year})",
           "data":list(data.values()),"backgroundColor":["#1abc9c","#2ecc71","#27ae60","#f39c12","#3498db"]}]},
           "options":{"title":_title(f"Renewable Electricity Share ({year})"),"legend":_legend(),"scales":_axes(x_label="Share (%)",x_min=0,x_max=100)}}
    return make_chart(cfg,500,300)+f"\n\n<sub>Source: World Bank [EG.ELC.RNEW.ZS](https://data.worldbank.org/indicator/EG.ELC.RNEW.ZS)</sub>"

def get_co2_emissions():
    iso = {"CHN":"China","USA":"USA","IND":"India","RUS":"Russia","JPN":"Japan"}
    fb  = {"China":11500,"USA":5000,"India":2900,"Russia":1700,"Japan":1100}
    raw, year = _wb_fetch("EN.ATM.CO2E.KT", iso, fb)
    data = {k:round(v/1000,1) for k,v in raw.items()} if year!="est." else fb
    cfg = {"type":"bar","data":{"labels":list(data.keys()),"datasets":[{"label":f"CO₂ Mt/year ({year})",
           "data":list(data.values()),"backgroundColor":["#e74c3c","#3498db","#f39c12","#9b59b6","#1abc9c"]}]},
           "options":{"title":_title(f"CO₂ Emissions by Country ({year})"),"legend":_legend(),"scales":_axes(y_label="Million Tonnes/year",y_min=0)}}
    return make_chart(cfg,500,300)+f"\n\n<sub>Source: World Bank [EN.ATM.CO2E.KT](https://data.worldbank.org/indicator/EN.ATM.CO2E.KT)</sub>"

def get_population():
    iso = {"IND":"India","CHN":"China","USA":"USA","IDN":"Indonesia","PAK":"Pakistan","BRA":"Brazil","NGA":"Nigeria","BGD":"Bangladesh"}
    fb  = {"India":1.43e9,"China":1.42e9,"USA":3.34e8,"Indonesia":2.77e8,"Pakistan":2.31e8,"Brazil":2.15e8,"Nigeria":2.17e8,"Bangladesh":1.73e8}
    data, year = _wb_fetch("SP.POP.TOTL", iso, fb)
    vals = [round(v/1e9,3) for v in data.values()]
    cfg = {"type":"bar","data":{"labels":list(data.keys()),"datasets":[{"label":f"Population Billions ({year})",
           "data":vals,"backgroundColor":"#3498db"}]},
           "options":{"title":_title(f"Population — Major Nations ({year})"),"legend":_legend(),"scales":_axes(y_label="Billions",y_min=0)}}
    return make_chart(cfg,560,300)+f"\n\n<sub>Source: World Bank [SP.POP.TOTL](https://data.worldbank.org/indicator/SP.POP.TOTL)</sub>"

def get_life_expectancy():
    iso = {"JPN":"Japan","HKG":"Hong Kong","CHE":"Switzerland","AUS":"Australia","USA":"USA","CHN":"China","IND":"India","NGA":"Nigeria"}
    fb  = {"Japan":84,"Hong Kong":85,"Switzerland":84,"Australia":83,"USA":77,"China":78,"India":70,"Nigeria":53}
    data, year = _wb_fetch("SP.DYN.LE00.IN", iso, fb)
    vals = [round(v,1) for v in data.values()]
    cfg = {"type":"horizontalBar","data":{"labels":list(data.keys()),"datasets":[{"label":f"Life Expectancy Years ({year})",
           "data":vals,"backgroundColor":["#2ecc71" if v>=80 else "#f39c12" if v>=70 else "#e74c3c" for v in vals]}]},
           "options":{"title":_title(f"Life Expectancy at Birth ({year})"),"legend":_legend(),"scales":_axes(x_label="Years",x_min=40,x_max=90)}}
    return make_chart(cfg,500,300)+f"\n\n<sub>Source: World Bank [SP.DYN.LE00.IN](https://data.worldbank.org/indicator/SP.DYN.LE00.IN)</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# DISEASE · disease.sh (COVID-19)
# ══════════════════════════════════════════════════════════════════════════════
def get_disease_stats():
    g = get_json("https://disease.sh/v3/covid-19/all")
    c = get_json("https://disease.sh/v3/covid-19/countries?sort=cases&limit=8")
    lines = ["#### Global COVID-19 Cumulative Summary\n"]
    if g:
        lines.append(f"| Cases | Deaths | Recovered |\n|------:|-------:|----------:|")
        lines.append(f"| {g.get('cases',0):,} | {g.get('deaths',0):,} | {g.get('recovered',0):,} |")
    lines.append("\n#### Top Countries by Cases\n")
    if c:
        lines.append("| Country | Cases | Deaths | Tests/1M |")
        lines.append("|:--------|------:|-------:|---------:|")
        for x in c[:8]:
            lines.append(f"| {x.get('country','—')[:15]} | {x.get('cases',0):,} | {x.get('deaths',0):,} | {x.get('testsPerOneMillion',0):,.0f} |")
    lines.append("\n<sub>Source: [disease.sh](https://disease.sh) — no auth</sub>")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# FOREX · Frankfurter / ECB
# ══════════════════════════════════════════════════════════════════════════════
def get_forex():
    data = get_json("https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY,INR,CNY,BRL,CHF,AUD,CAD")
    if not data: return "_Forex data unavailable_"
    date = data.get("date","—"); rates = data.get("rates",{})
    rows = [f"**USD Base Rates — {date} (ECB)**\n","| Currency | Rate vs USD |","|:---------|------------:|"]
    for cur, rate in sorted(rates.items()):
        rows.append(f"| {cur} | {rate:.4f} |")
    rows.append("\n<sub>Source: [Frankfurter.app](https://www.frankfurter.app) — ECB rates, no auth</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# FLIGHT TRAFFIC · OpenSky Network
# ══════════════════════════════════════════════════════════════════════════════
def get_flight_traffic():
    data = get_json("https://opensky-network.org/api/states/all")
    if not data or "states" not in data or not data["states"]:
        return "_Flight traffic data unavailable (OpenSky rate limited)_"
    states = data["states"]; total = len(states)
    cc = {}
    for s in states:
        o = s[2] if s[2] else "Unknown"
        cc[o] = cc.get(o,0) + 1
    top = sorted(cc.items(), key=lambda x: x[1], reverse=True)[:8]
    rows = [f"**Total airborne aircraft (live): {total:,}**\n","| Origin Country | Aircraft |","|:--------------|--------:|"]
    for country, count in top:
        rows.append(f"| {country} | {count:,} |")
    rows.append("\n<sub>Source: [OpenSky Network](https://opensky-network.org) — anonymous, live</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# COUNTRY DEMOGRAPHICS · REST Countries
# ══════════════════════════════════════════════════════════════════════════════
def get_country_signals():
    data = get_json("https://restcountries.com/v3.1/all?fields=name,population,area,region,subregion")
    if not data: return "_Country data unavailable_"
    top = sorted(data, key=lambda x: x.get("population",0), reverse=True)[:10]
    rows = ["| Country | Region | Population | Area (km²) | Density |","|:--------|:-------|----------:|-----------:|--------:|"]
    for c in top:
        name = c.get("name",{}).get("common","—"); region = c.get("subregion",c.get("region","—"))
        pop = c.get("population",0); area = c.get("area",1) or 1
        rows.append(f"| {name} | {region} | {pop:,} | {area:,.0f} | {round(pop/area,1)} /km² |")
    rows.append("\n<sub>Source: [REST Countries](https://restcountries.com) — no auth</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# ARXIV RESEARCH FEED · 10 domains
# ══════════════════════════════════════════════════════════════════════════════
def get_arxiv():
    categories = [("astro-ph","Astrophysics"),("quant-ph","Quantum Physics"),("cs.AI","AI / CS"),
                  ("cs.LG","Machine Learning"),("cond-mat","Condensed Matter"),("q-bio.NC","Neuroscience"),
                  ("econ.GN","Economics"),("physics","Physics"),("math.DS","Dynamical Systems"),("stat.ML","Stat. ML")]
    papers = []
    for cat, label in categories:
        url  = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending"
        root = get_xml(url)
        if not root: continue
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:1]:
            title   = entry.find("atom:title", ns).text.strip().replace("\n"," ")[:80]
            aid     = entry.find("atom:id", ns).text.split("/abs/")[-1]
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)[:2]]
            pub     = entry.find("atom:published", ns).text[:10]
            papers.append((label, title, aid, ", ".join(authors), pub))
    if not papers: return "_No papers fetched._"
    rows = ["| # | Domain | Title | Authors | Date |","|:-:|:-------|:------|:--------|-----:|"]
    for i,(label,title,aid,authors,pub) in enumerate(papers,1):
        rows.append(f"| {i} | {label} | [{title}...](https://arxiv.org/abs/{aid}) | {authors} | {pub} |")
    return "\n".join(rows) + "\n\n<sub>Source: [arXiv.org](https://arxiv.org) — no auth</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# GITHUB TRENDING
# ══════════════════════════════════════════════════════════════════════════════
def get_github_trending():
    since = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data  = get_json(f"https://api.github.com/search/repositories?q=created:>{since}&sort=stars&order=desc&per_page=8")
    if not data or "items" not in data: return "_GitHub data unavailable_"
    rows = ["| Repo | Stars | Language | Description |","|:-----|------:|:---------|:------------|"]
    for r in data["items"][:8]:
        rows.append(f"| [{r.get('full_name','—')[:35]}]({r.get('html_url','#')}) | {r.get('stargazers_count',0):,} | {r.get('language','—') or '—'} | {(r.get('description','') or '')[:45]} |")
    rows.append("\n<sub>Source: [GitHub API](https://docs.github.com/en/rest) — no auth, 10 req/min</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# WIKIPEDIA TRENDING · Wikimedia Pageviews
# ══════════════════════════════════════════════════════════════════════════════
def get_wikipedia_trending():
    from datetime import timedelta
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{yesterday.strftime('%Y/%m/%d')}"
    data = get_json(url)
    if not data: return "_Wikipedia trends unavailable_"
    articles = data.get("items",[{}])[0].get("articles",[])
    rows = ["| # | Article | Pageviews |","|:-:|:--------|----------:|"]
    count = 0
    for a in articles:
        title = a.get("article","—").replace("_"," ")
        if title in ("Main Page","Special:Search","Wikipedia:Featured_pictures","-",""): continue
        rows.append(f"| {count+1} | [{title}](https://en.wikipedia.org/wiki/{a.get('article','').replace(' ','_')}) | {a.get('views',0):,} |")
        count += 1
        if count >= 8: break
    rows.append(f"\n<sub>Source: [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/) — {yesterday.strftime('%Y-%m-%d')}, no auth</sub>")
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# FISHING · NOAA FishWatch + GBIF
# ══════════════════════════════════════════════════════════════════════════════
def get_fishing():
    from datetime import timedelta
    lines = []
    fw = get_json("https://www.fishwatch.gov/api/species")
    if fw and isinstance(fw, list):
        marine = [s for s in fw if s.get("Fishing Rate") and s.get("Population Status")]
        lines.append("#### US Fish Stock Status — NOAA FishWatch\n")
        lines.append("| Species | Fishing Rate | Population Status |")
        lines.append("|:--------|:-------------|:------------------|")
        for s in marine[:10]:
            lines.append(f"| {(s.get('Species Name') or '—')[:30]} | {(s.get('Fishing Rate') or '—')[:25]} | {(s.get('Population Status') or '—')[:25]} |")
        lines.append(f"\n_Total species in NOAA database: {len(fw)}_\n")
    marine_taxa = [("Gadus morhua","Atlantic Cod"),("Thunnus thynnus","Atlantic Bluefin Tuna"),
                   ("Salmo salar","Atlantic Salmon"),("Clupea harengus","Atlantic Herring")]
    gbif_rows = []
    for sci, common in marine_taxa:
        d = get_json(f"https://api.gbif.org/v1/occurrence/search?scientificName={urllib.parse.quote(sci)}&limit=1&hasCoordinate=true")
        if d: gbif_rows.append((common, sci, f"{d.get('count',0):,}"))
    if gbif_rows:
        lines.append("#### GBIF Marine Species — Observation Records\n")
        lines.append("| Common Name | Scientific Name | GBIF Occurrences |")
        lines.append("|:------------|:----------------|----------------:|")
        for common, sci, count in gbif_rows:
            lines.append(f"| {common} | _{sci}_ | {count} |")
    if not lines: return "_Fishing data unavailable_"
    lines.append("\n<sub>Sources: [NOAA FishWatch](https://www.fishwatch.gov/developers) · [GBIF](https://www.gbif.org/developer/occurrence)</sub>")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# VISUAL — Wikimedia POTD + Protein Structure
# ══════════════════════════════════════════════════════════════════════════════
def get_apod_visual():
    today = datetime.now(timezone.utc)
    url   = f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/{today.strftime('%Y/%m/%d')}"
    data  = get_json(url)
    if data:
        img  = data.get("image", {})
        title = img.get("title","Wikimedia POTD").replace("File:","").replace("_"," ")
        desc_obj = img.get("description",{})
        desc = desc_obj.get("text","") if isinstance(desc_obj,dict) else str(desc_obj)
        desc = (desc[:250]+"...") if len(desc)>250 else desc
        thumb = (img.get("thumbnail",{}) or {}).get("source","")
        if not thumb: thumb = (img.get("image",{}) or {}).get("source","")
        wiki_page = f"https://en.wikipedia.org/wiki/Wikipedia:Picture_of_the_day/{today.strftime('%B_%-d,_%Y')}"
        if thumb and _download_image(thumb, "assets/apod.jpg"):
            return (f"[![{title}](./assets/apod.jpg)]({wiki_page})\n\n**{title}**\n\n_{desc}_\n\n"
                    f"<sub>Source: [Wikimedia Commons](https://commons.wikimedia.org)</sub>")
    return "_([Browse Wikimedia Commons](https://commons.wikimedia.org))_"

def get_protein_visual():
    entries = [("6LU7","COVID-19 Main Protease"),("1BNA","B-DNA Double Helix"),("2HHB","Haemoglobin"),
               ("1MBO","Myoglobin"),("4HHB","Deoxyhaemoglobin"),("1CRN","Crambin")]
    pdb, name = entries[datetime.now().day % len(entries)]
    if _download_image(f"https://cdn.rcsb.org/images/structures/{pdb.lower()}_assembly-1.jpeg","assets/protein.jpg"):
        return (f'<img src="./assets/protein.jpg" width="100%" style="border-radius:6px;" />\n\n'
                f"**{name}** &nbsp; `{pdb}`\n\n<sub>Source: [RCSB PDB](https://www.rcsb.org/structure/{pdb})</sub>")
    return f"**{name}** `{pdb}`\n\n_([View 3D Structure](https://www.rcsb.org/structure/{pdb}))_"

    # ══════════════════════════════════════════════════════════════════════════════
# CELESTRAK — Full NORAD Satellite Catalog
# ══════════════════════════════════════════════════════════════════════════════
def get_celestrak():
    groups = [("stations","Space Stations"),("active","All Active Satellites"),
              ("starlink","Starlink (SpaceX)"),("oneweb","OneWeb"),("planet","Planet Labs"),
              ("gps-ops","GPS — operational"),("glo-ops","GLONASS — operational"),
              ("galileo","Galileo (EU)"),("beidou","BeiDou (China)"),("geo","Geostationary (GEO)"),
              ("weather","Weather Satellites"),("noaa","NOAA"),("goes","GOES"),
              ("resource","Earth Resources"),("cubesat","CubeSats"),("debris","Debris (selected)")]
    pal = ["#4FC3F7","#00bcd4","#1abc9c","#2ecc71","#27ae60","#f39c12","#e67e22",
           "#e74c3c","#9b59b6","#8e44ad","#3498db","#2980b9","#16a085","#d35400","#c0392b","#7f8c8d"]
    labels = []; counts = []
    table  = "| Category | Tracked Objects |\n|:---------|----------------:|\n"
    for gid, label in groups:
        txt = get_text(f"https://celestrak.org/NORAD/elements/gp.php?GROUP={gid}&FORMAT=TLE")
        cnt = len([l for l in (txt or "").splitlines() if l.strip()]) // 3
        labels.append(label); counts.append(cnt)
        table += f"| {label} | {cnt:,} |\n"
        time.sleep(0.3)
    cfg = {"type":"horizontalBar","data":{"labels":labels,"datasets":[{"label":"Objects tracked",
           "data":counts,"backgroundColor":pal[:len(labels)]}]},
           "options":{"title":title_opt("CelesTrak — NORAD Tracked Objects by Category"),
                      "legend":legend_opt,"scales":axes(xl="Object Count",xn=0)}}
    return (chart(cfg,900,520)+"\n\n"+table+
            "\n<sub>Source: [CelesTrak](https://celestrak.org) — no auth, updated daily</sub>")


# ══════════════════════════════════════════════════════════════════════════════
# KEY SATELLITE ORBITAL PARAMETERS (TLE-derived) · CelesTrak
# ══════════════════════════════════════════════════════════════════════════════
def get_key_satellites():
    MU = 398600.4418; RE = 6378.135
    sats = [("25544","ISS (ZARYA)"),("48274","CSS Tiangong"),("43013","NOAA-20"),
            ("41335","GOES-16"),("51850","GOES-18"),("40697","Sentinel-2A"),
            ("42063","Sentinel-2B"),("39634","Landsat 8"),("49260","Landsat 9"),
            ("28654","Terra EOS AM-1"),("27424","Aqua EOS PM-1"),("37849","Suomi NPP"),
            ("43205","ICESat-2"),("25338","GPS IIR-2"),("44985","Starlink-1007")]
    rows = []
    for norad, name in sats:
        txt = get_text(f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=TLE")
        if not txt: continue
        lines = [l for l in txt.splitlines() if l.strip()]
        if len(lines) < 3: continue
        try:
            l2 = lines[2]
            mm = float(l2[52:63]); ecc = float("0."+l2[26:33]); inc = float(l2[8:16])
            n  = mm * 2 * math.pi / 86400; a = (MU/n**2)**(1/3)
            apo = round(a*(1+ecc)-RE,0); per = round(a*(1-ecc)-RE,0)
            period = round(1440/mm,1)
            otype = "LEO" if apo<2000 else ("MEO" if apo<35000 else "GEO")
            rows.append((name,norad,f"{inc:.1f}",str(int(per)),str(int(apo)),str(period),otype))
        except: pass
        time.sleep(0.15)
    if not rows: return "_TLE data unavailable_"
    tbl = "| Satellite | NORAD | Inc° | Perigee | Apogee | Period | Orbit |\n"
    tbl += "|:----------|------:|-----:|--------:|-------:|-------:|:------|\n"
    for n,nd,inc,pe,ap,pr,ot in rows:
        tbl += f"| {n} | {nd} | {inc} | {pe} km | {ap} km | {pr} min | {ot} |\n"
    return tbl+"\n<sub>Source: [CelesTrak GP](https://celestrak.org) — no auth, TLE-derived params</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# NASA DONKI — CMEs, Flares, Storms (7 days)
# ══════════════════════════════════════════════════════════════════════════════
def get_donki():
    from datetime import timedelta
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")
    out   = []
    cmes = get_json(f"https://api.nasa.gov/DONKI/CME?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if cmes:
        out.append(f"**Coronal Mass Ejections (CME): {len(cmes)} events in last 7 days**\n")
        out.append("| Date UTC | Speed | Type | Note |")
        out.append("|:---------|------:|:-----|:-----|")
        for c in cmes[:6]:
            an = (c.get("cmeAnalyses") or [{}])[0]
            out.append(f"| {c.get('startTime','—')[:16]} | {an.get('speed','—')} km/s | {an.get('type','—')} | {str(an.get('note',''))[:40]} |")
        out.append("")
    flares = get_json(f"https://api.nasa.gov/DONKI/FLR?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if flares:
        out.append(f"**Solar Flares: {len(flares)} events in last 7 days**\n")
        out.append("| Date UTC | Class | End Time | Linked CME |")
        out.append("|:---------|:------|:---------|:-----------|")
        for f in flares[:6]:
            out.append(f"| {f.get('beginTime','—')[:16]} | {f.get('classType','—')} | {f.get('endTime','—')[:16]} | {'Yes' if f.get('linkedEvents') else 'No'} |")
        out.append("")
    gsts = get_json(f"https://api.nasa.gov/DONKI/GST?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if gsts:
        out.append(f"**Geomagnetic Storms: {len(gsts)} events in last 7 days**\n")
        out.append("| Date UTC | Max Kp | G-Scale | Satellite Impact |")
        out.append("|:---------|-------:|:--------|:-----------------|")
        for g in gsts[:5]:
            kps = [k.get("kpIndex",0) for k in (g.get("allKpIndex") or [])]
            km  = max(kps, default=0)
            gs  = "G5" if km>=9 else "G4" if km>=8 else "G3" if km>=7 else "G2" if km>=6 else "G1"
            imp = "Widespread HF blackout" if km>=8 else "HF radio disruption" if km>=6 else "GPS affected"
            out.append(f"| {g.get('startTime','—')[:16]} | {km} | {gs} | {imp} |")
    if not out: out.append("_No significant space weather events in last 7 days._")
    out.append(f"\n<sub>Source: [NASA DONKI](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) — DEMO_KEY</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# NASA EPIC — Earth from DSCOVR at L1 orbit
# ══════════════════════════════════════════════════════════════════════════════
def get_epic():
    data = get_json(f"https://api.nasa.gov/EPIC/api/natural?api_key={NASA_KEY}")
    if not data: return "_EPIC imagery unavailable_"
    latest   = data[0]
    img_name = latest["image"]
    date_str = latest["date"][:10].replace("-","/")
    caption  = (latest.get("caption") or "")[:200]
    ds_pos   = latest.get("dscovr_j2000_position",{})
    dist = round(math.sqrt(sum(ds_pos.get(k,0)**2 for k in ["x","y","z"])),0) if ds_pos else 0
    img_url = f"https://api.nasa.gov/EPIC/archive/natural/{date_str}/jpg/{img_name}.jpg?api_key={NASA_KEY}"
    out = f"**DSCOVR/EPIC — {latest['date'][:16]} UTC**\n\n_{caption}_\n\n"
    if save_img(img_url, "assets/epic.jpg"):
        out += "![Earth from DSCOVR L1](./assets/epic.jpg)\n\n"
    cc = latest.get("centroid_coordinates",{})
    out += f"""| EPIC Param | Value |
|:-----------|------:|
| Centroid Lat | {cc.get('lat',0):.2f}° |
| Centroid Lon | {cc.get('lon',0):.2f}° |
| DSCOVR distance | {dist:,.0f} km from Earth |
| Images today | {len(data)} |
"""
    out += f"\n<sub>Source: [NASA EPIC](https://api.nasa.gov) — DSCOVR at Sun-Earth L1, DEMO_KEY</sub>"
    return out


# ══════════════════════════════════════════════════════════════════════════════
# NASA FIRMS — Active fires (MODIS/VIIRS). Set FIRMS_MAP_KEY secret to enable.
# ══════════════════════════════════════════════════════════════════════════════
def get_firms():
    out = []
    if FIRMS_KEY:
        url  = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_KEY}/VIIRS_NOAA20_NRT/world/1"
        text = get_text(url)
        if text:
            try:
                rows   = list(csv.DictReader(io.StringIO(text)))
                total  = len(rows)
                points = []
                regions = {"N.America":0,"S.America":0,"Africa":0,"Europe":0,"Asia":0,"Australia":0,"Other":0}
                for row in rows:
                    try:
                        lat=float(row.get("latitude",0)); lon=float(row.get("longitude",0)); frp=float(row.get("frp",3))
                        points.append({"x":round(lon,1),"y":round(lat,1),"r":min(round(frp/5,1),10)})
                        if   lon<-30 and lat>0:  regions["N.America"]+=1
                        elif lon<-30 and lat<=0: regions["S.America"]+=1
                        elif -20<=lon<=55 and lat<40: regions["Africa"]+=1
                        elif lon<40 and lat>=35: regions["Europe"]+=1
                        elif lon>40 and lat>0:   regions["Asia"]+=1
                        elif lon>110 and lat<0:  regions["Australia"]+=1
                        else: regions["Other"]+=1
                    except: pass
                cfg = {"type":"bubble","data":{"datasets":[{"label":f"Active fires (bubble=FRP)","data":points[:350],
                       "backgroundColor":"rgba(255,80,20,0.5)","borderColor":"rgba(255,120,40,0.8)","borderWidth":0.5}]},
                       "options":{"title":title_opt(f"VIIRS NOAA-20 Active Fires — {total:,} detections (24h)"),
                                  "legend":legend_opt,"scales":axes("Longitude","Latitude",-180,180,-90,90)}}
                out.append(f"**Active fire detections (VIIRS NOAA-20, last 24h): {total:,}**\n")
                out.append(chart(cfg,900,420))
                out.append("\n| Region | Detections |\n|:-------|----------:|")
                for reg,cnt in sorted(regions.items(),key=lambda x:-x[1]):
                    out.append(f"| {reg} | {cnt:,} |")
            except Exception as e:
                out.append(f"_FIRMS parse error: {e}_")
    else:
        out.append("_Set `FIRMS_MAP_KEY` secret to enable live fire map._\n")
        out.append("Register free at [firms.modaps.eosdis.nasa.gov/api/map_key/](https://firms.modaps.eosdis.nasa.gov/api/map_key/)\n")
        out.append("| Satellite | Sensor | Resolution | Latency |")
        out.append("|:----------|:-------|:----------:|--------:|")
        for row in [("Terra","MODIS","1 km","~3 hrs"),("Aqua","MODIS","1 km","~3 hrs"),
                    ("Suomi NPP","VIIRS","375 m","~3 hrs"),("NOAA-20","VIIRS","375 m","~3 hrs"),
                    ("NOAA-21","VIIRS","375 m","~3 hrs"),("Landsat 8/9","OLI","30 m","~16 days")]:
            out.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
    out.append(f"\n<sub>Source: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) — MODIS+VIIRS, free MAP_KEY</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# NASA GIBS — Global satellite imagery layers (no auth)
# ══════════════════════════════════════════════════════════════════════════════
def get_gibs():
    from datetime import timedelta
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    base = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
    layers = [
        ("VIIRS_SNPP_CorrectedReflectance_TrueColor","Suomi NPP VIIRS True Color","assets/gibs_viirs.png"),
        ("MODIS_Terra_CorrectedReflectance_TrueColor","Terra MODIS True Color","assets/gibs_terra.png"),
        ("GHRSST_L4_G1SST_Sea_Surface_Temperature","Sea Surface Temperature","assets/gibs_sst.png"),
        ("MODIS_Terra_Land_Surface_Temp_Day","Land Surface Temperature (Day)","assets/gibs_lst.png"),
    ]
    os.makedirs("assets", exist_ok=True)
    out = ["#### NASA GIBS — Live Satellite Imagery (no auth required)\n"]
    imgs = []
    for layer_id, label, asset in layers:
        url = (f"{base}?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS={layer_id}"
               f"&CRS=EPSG:4326&BBOX=-90,-180,90,180&WIDTH=720&HEIGHT=360&FORMAT=image/png&TIME={yesterday}")
        if save_img(url, asset):
            imgs.append(f"**{label}**\n\n![{label}](./{asset})")
    out.extend(imgs if imgs else ["_GIBS imagery could not be downloaded_"])
    out.append(f"\n**GIBS WMS endpoint (no key):**\n```\nhttps://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi\n  ?SERVICE=WMS&REQUEST=GetMap&LAYERS={{LAYER_ID}}&CRS=EPSG:4326&BBOX=-90,-180,90,180\n  &WIDTH=720&HEIGHT=360&FORMAT=image/png&TIME={{YYYY-MM-DD}}\n```")
    out.append(f"\n<sub>Source: [NASA GIBS](https://www.earthdata.nasa.gov) — 1000+ layers, no auth, WMS/WMTS</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# NASA POWER — Satellite-derived meteorological data (no auth)
# ══════════════════════════════════════════════════════════════════════════════
def get_nasa_power():
    from datetime import timedelta
    today = datetime.now(timezone.utc)
    end_date   = (today - timedelta(days=2)).strftime("%Y%m%d")
    start_date = (today - timedelta(days=32)).strftime("%Y%m%d")
    cities = [("New York",40.71,-74.01),("London",51.51,-0.13),("Dubai",25.20,55.27),
              ("Tokyo",35.69,139.69),("Sydney",-33.87,151.21),("Mumbai",19.08,72.88)]
    rows = []
    for name, lat, lon in cities:
        url = (f"https://power.larc.nasa.gov/api/temporal/daily/point"
               f"?parameters=ALLSKY_SFC_SW_DWN,WS10M,T2M&community=RE"
               f"&longitude={lon}&latitude={lat}&start={start_date}&end={end_date}&format=JSON")
        data = get_json(url)
        if not data: continue
        try:
            props = data["properties"]["parameter"]
            sw_vals = [v for v in props.get("ALLSKY_SFC_SW_DWN",{}).values() if v!=-999]
            ws_vals = [v for v in props.get("WS10M",{}).values() if v!=-999]
            t_vals  = [v for v in props.get("T2M",{}).values() if v!=-999]
            rows.append((name,
                         round(sw_vals[-1],2) if sw_vals else "—",
                         round(ws_vals[-1],2) if ws_vals else "—",
                         round(t_vals[-1],1)  if t_vals  else "—"))
        except: pass
    if not rows: return "_NASA POWER data unavailable_\n\n<sub>Source: [NASA POWER](https://power.larc.nasa.gov/api/)</sub>"
    labels = [r[0] for r in rows]
    sw_vals = [r[1] if isinstance(r[1],float) else 0 for r in rows]
    c = chart({"type":"bar","data":{"labels":labels,"datasets":[{"label":"Solar Radiation (kW-hr/m2/day)",
               "data":sw_vals,"backgroundColor":["#f39c12","#4FC3F7","#e74c3c","#2ecc71","#9b59b6","#1abc9c"]}]},
               "options":{"title":title_opt("NASA POWER — Satellite Solar Radiation"),"legend":legend_opt,"scales":axes(yl="kW-hr/m2/day",yn=0)}},900,260)
    table = "| City | Solar Rad (kW-hr/m2/d) | Wind 10m (m/s) | Temp 2m (°C) |\n|:-----|----------------------:|---------------:|-------------:|\n"
    for name,sw,ws,t in rows:
        table += f"| {name} | {sw} | {ws} | {t} |\n"
    return c+"\n\n"+table+"\n<sub>Source: [NASA POWER](https://power.larc.nasa.gov/api/) — CERES/GEOS-5, no auth</sub>"


# ══════════════════════════════════════════════════════════════════════════════
# NASA WSA-Enlil Solar Wind Simulation
# ══════════════════════════════════════════════════════════════════════════════
def get_enlil():
    from datetime import timedelta
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")
    data  = get_json(f"https://api.nasa.gov/DONKI/WSAEnlilSimulations?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if not data: return "_WSA-Enlil data unavailable_\n\n<sub>Source: [NASA DONKI WSA-Enlil](https://api.nasa.gov)</sub>"
    out = [f"**WSA-Enlil Solar Wind Model Simulations — {len(data)} runs (last 14 days)**\n"]
    out.append("| Run Time | Estimated Shock Arrival | Earth-Directed | CME Count |")
    out.append("|:---------|:------------------------|:--------------:|----------:|")
    for sim in data[:8]:
        run_time = sim.get("simulationStartTime","—")[:16]
        impact   = sim.get("estimatedShock1ArrivalTime","None")
        if impact and impact != "None": impact = impact[:16]
        cmes     = len(sim.get("cmeInputs",[]))
        score    = "Yes" if sim.get("isEarthDirected") else "No"
        out.append(f"| {run_time} | {impact or 'None'} | {score} | {cmes} |")
    out.append("\n<sub>Source: [NASA DONKI WSA-Enlil](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) — DEMO_KEY</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# NASA MARS ROVERS — Curiosity + Perseverance latest photos
# ══════════════════════════════════════════════════════════════════════════════
def get_mars_rovers():
    out = []
    for rover, label in [("curiosity","Curiosity"),("perseverance","Perseverance")]:
        data = get_json(f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/latest_photos?api_key={NASA_KEY}")
        if not data or not data.get("latest_photos"): continue
        photos = data["latest_photos"]; p = photos[0]
        sol = p.get("sol","—"); cam = p.get("camera",{}).get("full_name","—"); earth_date = p.get("earth_date","—")
        img_url = p.get("img_src","")
        out.append(f"**{label}** — Sol {sol} ({earth_date}) — Camera: {cam}")
        if img_url and save_img(img_url, f"assets/mars_{rover}.jpg"):
            out.append(f"\n![{label} Mars photo](./assets/mars_{rover}.jpg)\n")
        out.append(f"_Photos available this sol: {len(photos)}_\n")
    out.append(f"<sub>Source: [NASA Mars Photos API](https://api.nasa.gov) — DEMO_KEY</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# NASA EXOPLANET ARCHIVE — Kepler/TESS/K2 discovered worlds
# ══════════════════════════════════════════════════════════════════════════════
def get_exoplanets():
    def count_query(where):
        url = (f"https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
               f"?query=select+count(*)+as+cnt+from+pscomppars{'+where+'+urllib.parse.quote(where) if where else ''}"
               f"&format=json")
        d = get_json(url)
        return d[0].get("cnt","—") if d else "—"

    total  = count_query("")
    kepler = count_query("disc_facility like '%Kepler%'")
    tess   = count_query("disc_facility like '%TESS%'")
    k2     = count_query("disc_facility like '%K2%'")
    hubble = count_query("disc_facility like '%Hubble%'")

    url_recent = ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
                  "?query=select+pl_name,disc_year,disc_facility,pl_orbper,pl_rade"
                  "+from+pscomppars+where+disc_facility+like+'%25TESS%25'"
                  "+order+by+disc_year+desc&format=json")
    recent = get_json(url_recent) or []

    disc_chart = chart({"type":"doughnut","data":{"labels":["Kepler","TESS","K2","Hubble & other"],
        "datasets":[{"data":[int(kepler) if str(kepler).isdigit() else 0,
                              int(tess) if str(tess).isdigit() else 0,
                              int(k2) if str(k2).isdigit() else 0,
                              int(hubble) if str(hubble).isdigit() else 0],
                     "backgroundColor":["#f39c12","#4FC3F7","#2ecc71","#9b59b6"],"borderWidth":1}]},
        "options":{"title":title_opt(f"Exoplanets Discovered by Space Telescopes (Total: {total})"),"legend":legend_opt}},600,320)

    table = "| Satellite / Telescope | Confirmed Exoplanets |\n|:----------------------|---------------------:|\n"
    for name,cnt in [("Kepler",kepler),("TESS",tess),("K2",k2),("Hubble (HST)",hubble)]:
        table += f"| {name} | {cnt:,} |\n" if str(cnt).isdigit() else f"| {name} | {cnt} |\n"
    table += f"| **Total confirmed** | **{total:,}** |\n" if str(total).isdigit() else f"| **Total** | **{total}** |\n"

    recent_table = ""
    if recent:
        recent_table = "\n**Recent TESS discoveries:**\n\n| Planet | Year | Period (days) | Radius (R⊕) |\n|:-------|-----:|--------------:|------------:|\n"
        for r in recent[:8]:
            period = f"{r.get('pl_orbper','—'):.2f}" if r.get("pl_orbper") else "—"
            radius = f"{r.get('pl_rade','—'):.2f}" if r.get("pl_rade") else "—"
            recent_table += f"| {r.get('pl_name','—')} | {r.get('disc_year','—')} | {period} | {radius} |\n"

    return (disc_chart+"\n\n"+table+recent_table+
            "\n<sub>Source: [NASA Exoplanet Archive TAP](https://exoplanetarchive.ipac.caltech.edu/TAP/sync) — no auth</sub>")


# ══════════════════════════════════════════════════════════════════════════════
# TLE SEARCH · tle.ivanstanojevic.me (no auth)
# ══════════════════════════════════════════════════════════════════════════════
def get_tle_search():
    searches = ["ISS","STARLINK","SENTINEL","NOAA","GOES","GPS"]
    out = ["#### TLE Search Results — tle.ivanstanojevic.me\n"]
    out.append("| Query | Results | Sample Satellite |")
    out.append("|:------|--------:|:----------------|")
    for q in searches:
        data = get_json(f"https://tle.ivanstanojevic.me/api/tle/?search={q}&page=1&page-size=5")
        if not data: continue
        total  = data.get("totalItems","—")
        sats   = data.get("member",[])
        sample = sats[0].get("name","—") if sats else "—"
        out.append(f"| {q} | {total:,} | {sample} |")
    out.append(f"\n<sub>Source: [tle.ivanstanojevic.me](https://tle.ivanstanojevic.me) — TLE search API, no auth</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# SatDB ETH Zurich — TLE archive (no auth)
# ══════════════════════════════════════════════════════════════════════════════
def get_satdb():
    sats = [(25544,"ISS"),(48274,"Tiangong CSS"),(41335,"GOES-16"),(40697,"Sentinel-2A"),(37849,"Suomi NPP"),(39634,"Landsat 8")]
    out = ["#### SatDB ETH Zurich — TLE Archive (sampled)\n"]
    out.append("| Satellite | NORAD | TLE Epoch | TLE Line 1 (truncated) |")
    out.append("|:----------|------:|:----------|:----------------------|")
    for norad, name in sats:
        data = get_json(f"https://satdb.ethz.ch/api/satellitedata/?norad-id={norad}&page-size=1&ordering=-datetime")
        if not data or not data.get("results"): continue
        r    = data["results"][0]
        tle  = r.get("norad_str","")
        lines = [l for l in tle.splitlines() if l.strip()]
        l1   = lines[1][:40]+"..." if len(lines)>1 else "—"
        epoch = lines[1][18:32].strip() if len(lines)>1 else "—"
        out.append(f"| {name} | {norad} | {epoch} | `{l1}` |")
        time.sleep(0.2)
    out.append(f"\n_SatDB archives TLEs hourly from CelesTrak. Query by NORAD ID + date range for historical orbit reconstruction._")
    out.append(f"\n<sub>Source: [SatDB ETH Zurich](https://satdb.ethz.ch/api-documentation/) — no auth</sub>")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# KeepTrack API — satellite position calculator (no auth)
# ══════════════════════════════════════════════════════════════════════════════
def get_keeptrack():
    MU = 398600.4418; RE = 6378.135
    key_sats = [(25544,"ISS"),(48274,"Tiangong"),(41335,"GOES-16"),(43013,"NOAA-20"),
                (40697,"Sentinel-2A"),(39634,"Landsat 8"),(37849,"Suomi NPP"),(43205,"ICESat-2")]
    out = ["#### KeepTrack API — Live Satellite Positions\n"]
    out.append("| Satellite | NORAD | Alt (km) | Inc° | Period |")
    out.append("|:----------|------:|---------:|-----:|-------:|")
    for norad, name in key_sats:
        data = get_json(f"https://api.keeptrack.space/v2/sat/{norad}")
        if not data: continue
        try:
            tle2 = data.get("TLE_LINE_2","")
            if len(tle2) < 63: continue
            mm  = float(tle2[52:63]); ecc = float("0."+tle2[26:33]); inc = float(tle2[8:16])
            n   = mm*2*math.pi/86400; a = (MU/n**2)**(1/3)
            alt = round(a*(1+ecc)-RE,0); period = round(1440/mm,1)
            out.append(f"| {name} | {norad} | {alt:.0f} | {inc:.1f}° | {period} min |")
        except: pass
        time.sleep(0.15)
    out.append(f"\n_KeepTrack covers 63,000+ objects. Pair with [ootk](https://github.com/thkruz/ootk) to propagate real-time lat/lon._")
    out.append(f"\n<sub>Source: [KeepTrack API](https://keeptrack.space/api) — no auth, 63k+ objects</sub>")
    return "\n".join(out)

    # ══════════════════════════════════════════════════════════════════════════════
# COMPLETE FREE SATELLITE & DATA API REFERENCE
# ══════════════════════════════════════════════════════════════════════════════
def get_api_reference():
    return """
| # | API | Auth | Endpoint | Data |
|:-:|:----|:----:|:---------|:-----|
| 1 | **wheretheiss.at** | None | `api.wheretheiss.at/v1/satellites/25544` | ISS position, altitude, velocity |
| 2 | **Open Notify** | None | `api.open-notify.org/astros.json` | Humans in space, ISS crew |
| 3 | **CelesTrak GP** | None | `celestrak.org/NORAD/elements/gp.php?GROUP=&FORMAT=TLE` | All NORAD TLEs by category |
| 4 | **CelesTrak SATCAT** | None | `celestrak.org/pub/satcat.csv` | Full satellite catalog CSV |
| 5 | **TLE API** | None | `tle.ivanstanojevic.me/api/tle/?search=` | TLE search by name |
| 6 | **NOAA SWPC Solar Wind** | None | `services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json` | Speed, density, temp |
| 7 | **NOAA SWPC IMF** | None | `services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json` | Bz, Bt magnetic field |
| 8 | **NOAA SWPC Kp** | None | `services.swpc.noaa.gov/json/planetary_k_index_1m.json` | Geomagnetic Kp index |
| 9 | **NOAA SWPC X-ray** | None | `services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json` | Solar X-ray flux |
| 10 | **NOAA SWPC Proton** | None | `services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json` | Proton flux |
| 11 | **NASA DONKI CME** | DEMO_KEY | `api.nasa.gov/DONKI/CME?startDate=&endDate=` | Coronal mass ejections |
| 12 | **NASA DONKI Flares** | DEMO_KEY | `api.nasa.gov/DONKI/FLR?startDate=&endDate=` | Solar flare events |
| 13 | **NASA DONKI Storms** | DEMO_KEY | `api.nasa.gov/DONKI/GST?startDate=&endDate=` | Geomagnetic storm events |
| 14 | **NASA NeoWs** | DEMO_KEY | `api.nasa.gov/neo/rest/v1/feed?start_date=` | Near Earth asteroid approaches |
| 15 | **NASA EPIC** | DEMO_KEY | `api.nasa.gov/EPIC/api/natural` | Earth photos from DSCOVR L1 |
| 16 | **NASA GIBS WMS** | None | `gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi` | 1000+ satellite imagery layers |
| 17 | **NASA FIRMS** | MAP_KEY | `firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_NOAA20_NRT/world/1` | MODIS+VIIRS fire detections |
| 18 | **NASA Mars Photos** | DEMO_KEY | `api.nasa.gov/mars-photos/api/v1/rovers/curiosity/latest_photos` | Curiosity/Perseverance photos |
| 19 | **NASA Exoplanet Archive** | None | `exoplanetarchive.ipac.caltech.edu/TAP/sync?query=` | Kepler/TESS discovered planets |
| 20 | **NASA POWER** | None | `power.larc.nasa.gov/api/temporal/daily/point` | Satellite-derived met data |
| 21 | **NASA WSA-Enlil** | DEMO_KEY | `api.nasa.gov/DONKI/WSAEnlilSimulations` | Heliospheric solar wind model |
| 22 | **USGS Earthquakes** | None | `earthquake.usgs.gov/fdsnws/event/1/query` | M5+ seismic events |
| 23 | **Open-Meteo** | None | `api.open-meteo.com/v1/forecast` | Weather forecast, no key |
| 24 | **NASA GISS** | None | `data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv` | Global temperature anomaly |
| 25 | **NOAA GML** | None | `gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt` | Atmospheric CO₂ Mauna Loa |
| 26 | **World Bank API** | None | `api.worldbank.org/v2/country/{iso}/indicator/{id}?format=json` | GDP, inflation, population, etc. |
| 27 | **disease.sh** | None | `disease.sh/v3/covid-19/all` | COVID-19 global stats |
| 28 | **Frankfurter ECB** | None | `api.frankfurter.app/latest?from=USD` | Foreign exchange rates |
| 29 | **OpenSky Network** | None | `opensky-network.org/api/states/all` | Live flight positions |
| 30 | **REST Countries** | None | `restcountries.com/v3.1/all` | Country demographics |
| 31 | **arXiv API** | None | `export.arxiv.org/api/query?search_query=cat:` | Research papers |
| 32 | **GitHub Search API** | None | `api.github.com/search/repositories` | Trending repositories |
| 33 | **Wikimedia Pageviews** | None | `wikimedia.org/api/rest_v1/metrics/pageviews/top/` | Wikipedia top articles |
| 34 | **Wikimedia Featured** | None | `api.wikimedia.org/feed/v1/wikipedia/en/featured/` | Picture of the Day |
| 35 | **RCSB PDB** | None | `cdn.rcsb.org/images/structures/{pdb}_assembly-1.jpeg` | Protein structure images |
| 36 | **GBIF** | None | `api.gbif.org/v1/occurrence/search` | Biodiversity occurrence records |
| 37 | **NOAA FishWatch** | None | `fishwatch.gov/api/species` | US fish stock status |
| 38 | **SatDB ETH Zurich** | None | `satdb.ethz.ch/api/satellitedata/?norad-id=` | Historical TLE archive |
| 39 | **KeepTrack API** | None | `api.keeptrack.space/v2/sat/{norad}` | Satellite TLE + orbital params |
| 40 | **Space-Track.org** | Free account | `space-track.org/basicspacedata/query` | Full USSPACECOM catalog |
| 41 | **N2YO API** | Free key | `api.n2yo.com/rest/v1/satellite/positions/{id}/` | Real-time satellite positions |
| 42 | **Copernicus STAC** | Free | `catalogue.dataspace.copernicus.eu/stac` | Sentinel imagery catalog |

<sub>DEMO_KEY = works without registration at 30 req/hr · MAP_KEY = register free at firms.modaps.eosdis.nasa.gov · Free account = register once</sub>
"""


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Global Satellite Signal Dashboard
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Loading README.md...")
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    steps = [
        # ── Timestamp ──────────────────────────────────────────────────────
        ("TIME",         get_timestamp),
        # ── Space & Satellites ─────────────────────────────────────────────
        ("SPACE_WEATHER",get_space_weather),
        ("ISS",          get_iss),
        ("CELESTRAK",    get_celestrak),
        ("SAT_PARAMS",   get_key_satellites),
        ("DONKI",        get_donki),
        ("EPIC",         get_epic),
        ("FIRMS",        get_firms),
        ("GIBS",         get_gibs),
        ("POWER",        get_nasa_power),
        ("ENLIL",        get_enlil),
        ("MARS",         get_mars_rovers),
        ("EXOPLANETS",   get_exoplanets),
        ("SATDB",        get_satdb),
        ("KEEPTRACK",    get_keeptrack),
        ("TLE_SEARCH",   get_tle_search),
        # ── Earth & Environment ────────────────────────────────────────────
        ("EARTHQUAKES",  get_earthquakes),
        ("NEOS",         get_neos),
        ("WEATHER",      get_weather_global),
        ("TEMP",         get_temperature_trend),
        ("CO2_ATMO",     get_co2),
        ("FISHING",      get_fishing),
        # ── Climate & Economics ────────────────────────────────────────────
        ("CLIMATE",      get_co2_emissions),
        ("ENERGY",       get_renewable_energy),
        ("GDP",          get_gdp_growth),
        ("INFLATION",    get_inflation),
        ("TRADE",        get_trade_balance),
        ("POPULATION",   get_population),
        ("LIFE_EXP",     get_life_expectancy),
        ("DISEASE",      get_disease_stats),
        ("FOREX",        get_forex),
        ("FLIGHTS",      get_flight_traffic),
        ("COUNTRY",      get_country_signals),
        # ── Research & Science ─────────────────────────────────────────────
        ("TICKER",       get_arxiv),
        ("GITHUB",       get_github_trending),
        ("WIKI_TRENDS",  get_wikipedia_trending),
        # ── Visual & Reference ─────────────────────────────────────────────
        ("APOD",         get_apod_visual),
        ("PROTEIN",      get_protein_visual),
        ("API_REF",      get_api_reference),
    ]

    for tag, fn in steps:
        print(f"  {tag}...", end=" ", flush=True)
        try:
            content = fn()
            readme  = inject(readme, tag, content)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("\nGlobal Satellite Signal Dashboard updated successfully.")


if __name__ == "__main__":
    main()