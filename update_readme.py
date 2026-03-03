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


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SPACE WEATHER (NOAA SWPC)
# APIs: plasma-2-hour, mag-2-hour, planetary_k_index_1m, xrays-1-day
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ISS LIVE POSITION (wheretheiss.at)
# ══════════════════════════════════════════════════════════════════════════════


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
# SECTION 16 — GLOBAL FISHING WATCH (fishing vessel activity, free API key)
# ══════════════════════════════════════════════════════════════════════════════
def get_fishing():
    """
    Global Fishing Watch public API — free registration key.
    Endpoint: https://globalfishingwatch.org/our-apis/
    
    Falls back to GBIF (Global Biodiversity Information Facility) marine
    species occurrence data — completely no-auth.
    
    Also queries FishWatch (NOAA) for fish stock status — no key.
    """
    lines = []

    # ── NOAA FishWatch — US fish stock status (no auth) ──────────────────────
    fw = get_json("https://www.fishwatch.gov/api/species")
    if fw and isinstance(fw, list):
        # Filter to marine species with stock status info
        marine = [s for s in fw if s.get("Fishing Rate") and s.get("Population Status")]
        lines.append("#### US Fish Stock Status — NOAA FishWatch\n")
        lines.append("| Species | Fishing Rate | Population Status | Habitat |")
        lines.append("|:--------|:-------------|:------------------|:--------|")
        for s in marine[:12]:
            name    = (s.get("Species Name") or s.get("Species Aliases") or "—")[:30]
            frate   = (s.get("Fishing Rate") or "—")[:25]
            pop     = (s.get("Population Status") or "—")[:25]
            habitat = (s.get("Habitat") or "—")[:30]
            lines.append(f"| {name} | {frate} | {pop} | {habitat} |")
        lines.append(f"\n_Total species in NOAA database: {len(fw)}_\n")

    # ── GBIF — Marine species occurrence counts (no auth) ────────────────────
    marine_taxa = [
        ("Gadus morhua",        "Atlantic Cod"),
        ("Thunnus thynnus",     "Atlantic Bluefin Tuna"),
        ("Salmo salar",         "Atlantic Salmon"),
        ("Clupea harengus",     "Atlantic Herring"),
        ("Engraulis encrasicolus", "European Anchovy"),
        ("Scomber scombrus",    "Atlantic Mackerel"),
        ("Merluccius merluccius","European Hake"),
        ("Solea solea",         "Common Sole"),
    ]
    gbif_rows = []
    for sci_name, common_name in marine_taxa:
        url  = (f"https://api.gbif.org/v1/occurrence/search"
                f"?scientificName={urllib.parse.quote(sci_name)}&limit=1&hasCoordinate=true")
        data = get_json(url)
        if data:
            count = data.get("count", 0)
            gbif_rows.append((common_name, sci_name, f"{count:,}"))

    if gbif_rows:
        lines.append("#### GBIF Marine Species — Observation Records\n")
        lines.append("| Common Name | Scientific Name | GBIF Occurrences |")
        lines.append("|:------------|:----------------|----------------:|")
        for common, sci, count in gbif_rows:
            lines.append(f"| {common} | _{sci}_ | {count} |")
        lines.append("")

    # ── GBIF — Recent marine occurrence events (last month) ──────────────────
    from datetime import timedelta
    today    = datetime.now(timezone.utc)
    month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    url_recent = (f"https://api.gbif.org/v1/occurrence/search"
                  f"?hasCoordinate=true&occurrenceStatus=PRESENT"
                  f"&taxonKey=11592253"   # Actinopterygii — ray-finned fishes
                  f"&eventDate={month_ago},{today_str}&limit=1")
    recent = get_json(url_recent)
    if recent:
        count = recent.get("count", 0)
        lines.append(f"_Ray-finned fish (Actinopterygii) observations in last 30 days: **{count:,}** records_\n")

    # ── Global Fishing Watch vessel stats (public summary, no key needed) ────
    # GFW public vessel search — basic stats without key
    gfw = get_json("https://gateway.api.globalfishingwatch.org/v3/vessels/search"
                   "?query=&datasets[0]=public-global-fishing-watch:v20231026&limit=1")
    if gfw and gfw.get("total"):
        total_vessels = gfw["total"]
        lines.append(f"_Global Fishing Watch — Vessels in public registry: **{total_vessels:,}**_\n")

    if not lines:
        return "_Fishing data unavailable — NOAA FishWatch and GBIF APIs returned no data_"

    lines.append("\n<sub>Sources: [NOAA FishWatch](https://www.fishwatch.gov/developers) · [GBIF](https://www.gbif.org/developer/occurrence) · [Global Fishing Watch](https://globalfishingwatch.org/our-apis/) — no auth / free key</sub>")
    return "\n".join(lines)


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


def get_timestamp():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"<sub>Last Updated: **{ts}**</sub>"

def get_iss():
    pos  = jget("https://api.wheretheiss.at/v1/satellites/25544")
    crew = jget("http://api.open-notify.org/astros.json")
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

    out.append("\n<sub>Sources: [wheretheiss.at](https://wheretheiss.at) · [Open Notify](http://open-notify.org/) — no auth, live</sub>")
    return "\n".join(out)

def get_space_weather():
    plasma = jget("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    mag    = jget("https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json")
    kpdata = jget("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json")
    xray   = jget("https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json")
    proton = jget("https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json")

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

    # Speed trend chart (last 72 readings ~ 6hrs)
    trend_chart = ""
    if plasma and len(plasma) > 2:
        pts = [None if not r[2] else round(float(r[2]), 0) for r in plasma[1:][-72:]]
        try:
            cfg = {
                "type": "line",
                "data": {"labels": [""]*len(pts),
                         "datasets": [{"label": "Solar Wind Speed km/s", "data": pts,
                                       "borderColor": sw_col,
                                       "backgroundColor": f"rgba(79,195,247,0.07)",
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
            "\n<sub>Source: [NOAA SWPC](https://www.swpc.noaa.gov) — space weather for satellite ops, no auth</sub>")

def get_neos():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data  = jget(f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key={NASA_KEY}")
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
    return out + f"\n<sub>Source: [NASA NeoWs](https://api.nasa.gov) — Near Earth Objects, DEMO_KEY</sub>"

def get_celestrak():
    groups = [
        ("stations",   "Space Stations"),
        ("active",     "All Active Satellites"),
        ("starlink",   "Starlink (SpaceX)"),
        ("oneweb",     "OneWeb"),
        ("planet",     "Planet Labs"),
        ("spire",      "Spire Global"),
        ("gps-ops",    "GPS — operational"),
        ("glo-ops",    "GLONASS — operational"),
        ("galileo",    "Galileo (EU)"),
        ("beidou",     "BeiDou (China)"),
        ("geo",        "Geostationary (GEO)"),
        ("weather",    "Weather Satellites"),
        ("noaa",       "NOAA"),
        ("goes",       "GOES"),
        ("resource",   "Earth Resources"),
        ("sarsat",     "SARSAT / Search & Rescue"),
        ("tdrss",      "Tracking & Data Relay"),
        ("cubesat",    "CubeSats"),
        ("debris",     "Debris (selected)"),
    ]
    pal = ["#4FC3F7","#00bcd4","#1abc9c","#2ecc71","#27ae60","#f39c12","#e67e22",
           "#e74c3c","#9b59b6","#8e44ad","#3498db","#2980b9","#16a085","#d35400",
           "#c0392b","#7f8c8d","#95a5a6","#bdc3c7","#34495e"]

    labels = []; counts = []
    table  = "| Category | Tracked Objects |\n|:---------|----------------:|\n"

    for gid, label in groups:
        txt = tget(f"https://celestrak.org/NORAD/elements/gp.php?GROUP={gid}&FORMAT=TLE")
        cnt = len([l for l in (txt or "").splitlines() if l.strip()]) // 3
        labels.append(label); counts.append(cnt)
        table += f"| {label} | {cnt:,} |\n"
        time.sleep(0.3)

    cfg = {
        "type": "horizontalBar",
        "data": {
            "labels": labels,
            "datasets": [{"label": "Objects tracked", "data": counts,
                          "backgroundColor": pal[:len(labels)]}]
        },
        "options": {
            "title":  title_opt("CelesTrak — NORAD Tracked Objects by Category"),
            "legend": legend_opt,
            "scales": axes(xl="Object Count", xn=0)
        }
    }
    return (chart(cfg, 900, 520) + "\n\n" + table +
            "\n<sub>Source: [CelesTrak](https://celestrak.org) — no auth, NORAD GP data updated daily</sub>")

def get_key_satellites():
    MU  = 398600.4418   # km³/s²
    RE  = 6378.135      # km Earth radius

    sats = [
        ("25544", "ISS (ZARYA)"),
        ("48274", "CSS Tiangong"),
        ("43013", "NOAA-20"),
        ("41335", "GOES-16"),
        ("43226", "GOES-17"),
        ("51850", "GOES-18"),
        ("40697", "Sentinel-2A"),
        ("42063", "Sentinel-2B"),
        ("39634", "Landsat 8"),
        ("49260", "Landsat 9"),
        ("28654", "Terra EOS AM-1"),
        ("27424", "Aqua EOS PM-1"),
        ("37849", "Suomi NPP"),
        ("43205", "ICESat-2"),
        ("25338", "GPS IIR-2"),
        ("44985", "Starlink-1007"),
        ("36516", "TanDEM-X"),
        ("32060", "ALOS"),
    ]

    rows = []
    for norad, name in sats:
        url  = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=TLE"
        txt  = tget(url)
        if not txt: continue
        lines = [l for l in txt.splitlines() if l.strip()]
        if len(lines) < 3: continue
        try:
            l2   = lines[2]
            mm   = float(l2[52:63])          # rev/day
            ecc  = float("0." + l2[26:33])
            inc  = float(l2[8:16])
            n    = mm * 2 * math.pi / 86400
            a    = (MU / n**2) ** (1/3)
            apo  = round(a * (1 + ecc) - RE, 0)
            per  = round(a * (1 - ecc) - RE, 0)
            period = round(1440 / mm, 1)
            otype = "LEO" if apo < 2000 else ("MEO" if apo < 35000 else "GEO")
            rows.append((name, norad, f"{inc:.1f}", str(int(per)), str(int(apo)), str(period), otype))
        except: pass
        time.sleep(0.15)

    if not rows: return "_TLE data unavailable_"
    tbl = "| Satellite | NORAD | Inc° | Perigee | Apogee | Period | Orbit |\n"
    tbl += "|:----------|------:|-----:|--------:|-------:|-------:|:------|\n"
    for n, nd, inc, pe, ap, pr, ot in rows:
        tbl += f"| {n} | {nd} | {inc} | {pe} km | {ap} km | {pr} min | {ot} |\n"
    return tbl + "\n<sub>Source: [CelesTrak GP](https://celestrak.org) — no auth, TLE-derived params</sub>"

def get_donki():
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")
    out   = []

    cmes = jget(f"https://api.nasa.gov/DONKI/CME?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if cmes:
        out.append(f"**Coronal Mass Ejections (CME): {len(cmes)} events in last 7 days**\n")
        out.append("| Date UTC | Speed | Type | Note |")
        out.append("|:---------|------:|:-----|:-----|")
        for c in cmes[:6]:
            an = (c.get("cmeAnalyses") or [{}])[0]
            out.append(f"| {c.get('startTime','—')[:16]} | {an.get('speed','—')} km/s | {an.get('type','—')} | {str(an.get('note',''))[:40]} |")
        out.append("")

    flares = jget(f"https://api.nasa.gov/DONKI/FLR?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if flares:
        out.append(f"**Solar Flares: {len(flares)} events in last 7 days**\n")
        out.append("| Date UTC | Class | End Time | Linked CME |")
        out.append("|:---------|:------|:---------|:-----------|")
        for f in flares[:6]:
            out.append(f"| {f.get('beginTime','—')[:16]} | {f.get('classType','—')} | {f.get('endTime','—')[:16]} | {'Yes' if f.get('linkedEvents') else 'No'} |")
        out.append("")

    gsts = jget(f"https://api.nasa.gov/DONKI/GST?startDate={start}&endDate={end}&api_key={NASA_KEY}")
    if gsts:
        out.append(f"**Geomagnetic Storms: {len(gsts)} events in last 7 days**\n")
        out.append("| Date UTC | Max Kp | G-Scale | Satellite Impact |")
        out.append("|:---------|-------:|:--------|:-----------------|")
        for g in gsts[:5]:
            kps = [k.get("kpIndex", 0) for k in (g.get("allKpIndex") or [])]
            km  = max(kps, default=0)
            gs  = "G5" if km>=9 else "G4" if km>=8 else "G3" if km>=7 else "G2" if km>=6 else "G1"
            imp = "Widespread HF blackout, power grid" if km >= 8 else "HF radio disruption" if km >= 6 else "GPS affected"
            out.append(f"| {g.get('startTime','—')[:16]} | {km} | {gs} | {imp} |")

    if not out:
        out.append("_No significant space weather events in last 7 days._")
    out.append(f"\n<sub>Source: [NASA DONKI](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) — Space Weather Database, DEMO_KEY</sub>")
    return "\n".join(out)

def get_epic():
    data = jget(f"https://api.nasa.gov/EPIC/api/natural?api_key={NASA_KEY}")
    if not data: return "_EPIC imagery unavailable_"

    latest   = data[0]
    img_name = latest["image"]
    date_str = latest["date"][:10].replace("-", "/")
    caption  = (latest.get("caption") or "")[:200]
    ds_pos   = latest.get("dscovr_j2000_position", {})

    dist = round(math.sqrt(sum(ds_pos.get(k,0)**2 for k in ["x","y","z"])), 0) if ds_pos else 0
    img_url = (f"https://api.nasa.gov/EPIC/archive/natural/{date_str}/jpg/{img_name}.jpg"
               f"?api_key={NASA_KEY}")

    out = f"**DSCOVR/EPIC — {latest['date'][:16]} UTC**\n\n_{caption}_\n\n"
    if save_img(img_url, "assets/epic.jpg"):
        out += "![Earth from DSCOVR L1](./assets/epic.jpg)\n\n"

    cc = latest.get("centroid_coordinates", {})
    out += f"""| EPIC Param | Value |
|:-----------|------:|
| Centroid Lat | {cc.get('lat', 0):.2f}° |
| Centroid Lon | {cc.get('lon', 0):.2f}° |
| DSCOVR distance | {dist:,.0f} km from Earth |
| Images today | {len(data)} |
"""
    out += f"\n<sub>Source: [NASA EPIC](https://api.nasa.gov) — DSCOVR at Sun-Earth L1, DEMO_KEY</sub>"
    return out

def get_firms():
    out = []
    if FIRMS_KEY:
        url  = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_KEY}/VIIRS_NOAA20_NRT/world/1"
        text = tget(url)
        if text:
            try:
                rows   = list(csv.DictReader(io.StringIO(text)))
                total  = len(rows)
                points = []
                regions = {"N.America": 0, "S.America": 0, "Africa": 0,
                           "Europe": 0, "Asia": 0, "Australia": 0, "Other": 0}
                for row in rows:
                    try:
                        lat = float(row.get("latitude", 0))
                        lon = float(row.get("longitude", 0))
                        frp = float(row.get("frp", 3))
                        points.append({"x": round(lon,1), "y": round(lat,1),
                                       "r": min(round(frp / 5, 1), 10)})
                        if   lon < -30 and lat >  0: regions["N.America"] += 1
                        elif lon < -30 and lat <= 0: regions["S.America"] += 1
                        elif -20<=lon<=55 and lat<40: regions["Africa"] += 1
                        elif lon < 40 and lat >= 35:  regions["Europe"] += 1
                        elif lon > 40 and lat > 0:    regions["Asia"] += 1
                        elif lon > 110 and lat < 0:   regions["Australia"] += 1
                        else: regions["Other"] += 1
                    except: pass

                cfg = {
                    "type": "bubble",
                    "data": {"datasets": [{"label": f"Active fires (bubble = FRP)",
                        "data": points[:350],
                        "backgroundColor": "rgba(255,80,20,0.5)",
                        "borderColor": "rgba(255,120,40,0.8)", "borderWidth": 0.5}]},
                    "options": {"title": title_opt(f"VIIRS NOAA-20 Active Fires — {total:,} detections (24h)"),
                        "legend": legend_opt,
                        "scales": axes("Longitude", "Latitude", -180, 180, -90, 90)}
                }
                out.append(f"**Active fire detections (VIIRS NOAA-20, last 24h): {total:,}**\n")
                out.append(chart(cfg, 900, 420))
                out.append("\n| Region | Detections |\n|:-------|----------:|")
                for reg, cnt in sorted(regions.items(), key=lambda x: -x[1]):
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

def get_gibs():
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    base = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"

    layers = [
        ("VIIRS_SNPP_CorrectedReflectance_TrueColor",    "Suomi NPP VIIRS True Color",      "assets/gibs_viirs.png"),
        ("MODIS_Terra_CorrectedReflectance_TrueColor",   "Terra MODIS True Color",           "assets/gibs_terra.png"),
        ("GHRSST_L4_G1SST_Sea_Surface_Temperature",      "Sea Surface Temperature",          "assets/gibs_sst.png"),
        ("MODIS_Terra_Land_Surface_Temp_Day",             "Land Surface Temperature (Day)",   "assets/gibs_lst.png"),
    ]

    os.makedirs("assets", exist_ok=True)
    out = ["#### NASA GIBS — Live Satellite Imagery (no auth required)\n"]

    imgs = []
    for layer_id, label, asset in layers:
        url = (f"{base}?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
               f"&LAYERS={layer_id}&CRS=EPSG:4326&BBOX=-90,-180,90,180"
               f"&WIDTH=720&HEIGHT=360&FORMAT=image/png&TIME={yesterday}")
        if save_img(url, asset):
            imgs.append(f"**{label}**\n\n![{label}](./{asset})")

    out.extend(imgs if imgs else ["_GIBS imagery could not be downloaded_"])
    out.append(f"""
**GIBS WMS endpoint (no key):**
```
https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi
  ?SERVICE=WMS&REQUEST=GetMap&LAYERS={{LAYER_ID}}
  &CRS=EPSG:4326&BBOX=-90,-180,90,180&WIDTH=720&HEIGHT=360
  &FORMAT=image/png&TIME={{YYYY-MM-DD}}
```

| Layer ID | Satellite | Product |
|:---------|:----------|:--------|
| VIIRS_SNPP_CorrectedReflectance_TrueColor | Suomi NPP | True color |
| MODIS_Terra_CorrectedReflectance_TrueColor | Terra | True color |
| MODIS_Aqua_CorrectedReflectance_TrueColor | Aqua | True color |
| GHRSST_L4_G1SST_Sea_Surface_Temperature | Multi-satellite | Sea surface temp |
| MODIS_Terra_Land_Surface_Temp_Day | Terra | Land surface temp day |
| MODIS_Terra_Land_Surface_Temp_Night | Terra | Land surface temp night |
| MODIS_Terra_Aerosol | Terra | Aerosol optical depth |
| AIRS_L2_Carbon_Monoxide_500hPa_Day | Aqua AIRS | CO at 500 hPa |
| MISR_Aerosol_Optical_Depth | Terra MISR | Multi-angle aerosol |
| Sentinel2_RGB | Sentinel-2 | True color (ESA) |
| OMI_Aerosol_Index | Aura OMI | UV aerosol index |
| MODIS_Terra_Sea_Ice | Terra | Sea ice extent |
| AMSRE_Sea_Ice_Brightness_Temp | Aqua AMSR-E | Sea ice brightness |
""")
    out.append(f"<sub>Source: [NASA GIBS](https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api) — 1000+ layers, no auth, WMS/WMTS</sub>")
    return "\n".join(out)

def get_exoplanets():
    def count_query(where):
        url = (f"https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
               f"?query=select+count(*)+as+cnt+from+pscomppars{'+where+'+urllib.parse.quote(where) if where else ''}"
               f"&format=json")
        d = jget(url)
        return d[0].get("cnt", "—") if d else "—"

    total   = count_query("")
    kepler  = count_query("disc_facility like '%Kepler%'")
    tess    = count_query("disc_facility like '%TESS%'")
    k2      = count_query("disc_facility like '%K2%'")
    hubble  = count_query("disc_facility like '%Hubble%'")

    # Recent TESS discoveries
    url_recent = ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
                  "?query=select+pl_name,disc_year,disc_facility,pl_orbper,pl_rade"
                  "+from+pscomppars+where+disc_facility+like+'%25TESS%25'"
                  "+order+by+disc_year+desc&format=json")
    recent = jget(url_recent) or []

    disc_chart = chart({
        "type": "doughnut",
        "data": {
            "labels": ["Kepler", "TESS", "K2", "Hubble & other space"],
            "datasets": [{"data": [int(kepler) if str(kepler).isdigit() else 0,
                                   int(tess) if str(tess).isdigit() else 0,
                                   int(k2) if str(k2).isdigit() else 0,
                                   int(hubble) if str(hubble).isdigit() else 0],
                          "backgroundColor": ["#f39c12","#4FC3F7","#2ecc71","#9b59b6"],
                          "borderWidth": 1}]
        },
        "options": {"title": title_opt(f"Exoplanets Discovered by Space Telescopes (Total: {total})"),
                    "legend": legend_opt}
    }, 600, 320)

    table = "| Satellite / Telescope | Confirmed Exoplanets |\n|:----------------------|---------------------:|\n"
    for name, cnt in [("Kepler", kepler), ("TESS", tess), ("K2", k2), ("Hubble (HST)", hubble)]:
        table += f"| {name} | {cnt:,} |\n" if str(cnt).isdigit() else f"| {name} | {cnt} |\n"
    table += f"| **Total confirmed** | **{total:,}** |\n" if str(total).isdigit() else f"| **Total** | **{total}** |\n"

    recent_table = ""
    if recent:
        recent_table = "\n**Recent TESS discoveries:**\n\n| Planet | Year | Period (days) | Radius (R⊕) |\n|:-------|-----:|--------------:|------------:|\n"
        for r in recent[:8]:
            period = f"{r.get('pl_orbper','—'):.2f}" if r.get("pl_orbper") else "—"
            radius = f"{r.get('pl_rade','—'):.2f}" if r.get("pl_rade") else "—"
            recent_table += f"| {r.get('pl_name','—')} | {r.get('disc_year','—')} | {period} | {radius} |\n"

    return (disc_chart + "\n\n" + table + recent_table +
            "\n<sub>Source: [NASA Exoplanet Archive TAP](https://exoplanetarchive.ipac.caltech.edu/TAP/sync) — no auth</sub>")

def get_mars_rovers():
    out = []
    rovers = [("curiosity", "Curiosity"), ("perseverance", "Perseverance")]
    for rover, label in rovers:
        data = jget(f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/latest_photos?api_key={NASA_KEY}")
        if not data or not data.get("latest_photos"): continue
        photos = data["latest_photos"]
        p      = photos[0]
        sol    = p.get("sol", "—")
        cam    = p.get("camera", {}).get("full_name", "—")
        earth_date = p.get("earth_date", "—")
        img_url = p.get("img_src", "")

        asset = f"assets/mars_{rover}.jpg"
        out.append(f"**{label}** — Sol {sol} ({earth_date}) — Camera: {cam}")
        if img_url and save_img(img_url, asset):
            out.append(f"\n![{label} Mars photo](./{asset})\n")
        out.append(f"_Photos available this sol: {len(photos)}_\n")

    out.append(f"<sub>Source: [NASA Mars Photos API](https://api.nasa.gov) — DEMO_KEY</sub>")
    return "\n".join(out)

def get_tle_search():
    searches = ["ISS", "STARLINK", "SENTINEL", "NOAA", "GOES", "GPS"]
    out = ["#### TLE Search Results — tle.ivanstanojevic.me\n"]
    out.append("| Query | Results | Sample Satellite |")
    out.append("|:------|--------:|:----------------|")
    for q in searches:
        data = jget(f"https://tle.ivanstanojevic.me/api/tle/?search={q}&page=1&page-size=5")
        if not data: continue
        total  = data.get("totalItems", "—")
        sats   = data.get("member", [])
        sample = sats[0].get("name","—") if sats else "—"
        out.append(f"| {q} | {total:,} | {sample} |")
    out.append(f"\n<sub>Source: [tle.ivanstanojevic.me](https://tle.ivanstanojevic.me) — TLE search API, no auth</sub>")
    return "\n".join(out)

def get_nasa_power():
    """
    NASA POWER (Prediction Of Worldwide Energy Resource)
    Satellite-derived solar radiation, wind, and temperature data.
    No API key, no auth. Data from CERES, GEWEX, GEOS-5 satellite models.
    """
    today     = datetime.now(timezone.utc)
    end_date  = (today - timedelta(days=2)).strftime("%Y%m%d")   # 2-day lag
    start_date = (today - timedelta(days=32)).strftime("%Y%m%d")

    # 6 major cities — solar radiation + wind signal
    cities = [
        ("New York",   40.71, -74.01),
        ("London",     51.51,  -0.13),
        ("Dubai",      25.20,  55.27),
        ("Tokyo",      35.69, 139.69),
        ("Sydney",    -33.87, 151.21),
        ("Mumbai",     19.08,  72.88),
    ]

    rows = []
    for name, lat, lon in cities:
        url = (f"https://power.larc.nasa.gov/api/temporal/daily/point"
               f"?parameters=ALLSKY_SFC_SW_DWN,WS10M,T2M"
               f"&community=RE&longitude={lon}&latitude={lat}"
               f"&start={start_date}&end={end_date}&format=JSON")
        data = jget(url)
        if not data: continue
        try:
            props = data["properties"]["parameter"]
            # Get latest non-fill value
            sw_vals = [v for v in props.get("ALLSKY_SFC_SW_DWN", {}).values() if v != -999]
            ws_vals = [v for v in props.get("WS10M", {}).values() if v != -999]
            t_vals  = [v for v in props.get("T2M", {}).values() if v != -999]
            sw = round(sw_vals[-1], 2) if sw_vals else "—"
            ws = round(ws_vals[-1], 2) if ws_vals else "—"
            t  = round(t_vals[-1],  1) if t_vals  else "—"
            rows.append((name, sw, ws, t))
        except: pass

    if not rows:
        return "_NASA POWER data unavailable_\n\n<sub>Source: [NASA POWER](https://power.larc.nasa.gov/api/) — satellite-derived met data, no auth</sub>"

    # Solar radiation bar chart
    labels = [r[0] for r in rows]
    sw_vals = [r[1] if isinstance(r[1], float) else 0 for r in rows]
    c = chart({
        "type": "bar",
        "data": {"labels": labels,
                 "datasets": [{"label": "Solar Radiation (kW-hr/m2/day)",
                               "data": sw_vals,
                               "backgroundColor": ["#f39c12","#4FC3F7","#e74c3c",
                                                   "#2ecc71","#9b59b6","#1abc9c"]}]},
        "options": {"title": title_opt("NASA POWER — Satellite Solar Radiation (today)"),
                    "legend": legend_opt, "scales": axes(yl="kW-hr/m2/day", yn=0)}
    }, 900, 260)

    table = "| City | Solar Rad (kW-hr/m2/d) | Wind 10m (m/s) | Temp 2m (C) |\n"
    table += "|:-----|----------------------:|---------------:|------------:|\n"
    for name, sw, ws, t in rows:
        table += f"| {name} | {sw} | {ws} | {t} |\n"

    return (c + "\n\n" + table +
            "\n<sub>Source: [NASA POWER](https://power.larc.nasa.gov/api/) — CERES/GEOS-5 satellite data, no auth</sub>")

def get_enlil():
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    end   = today.strftime("%Y-%m-%d")
    data  = jget(f"https://api.nasa.gov/DONKI/WSAEnlilSimulations?startDate={start}&endDate={end}&api_key={NASA_KEY}")

    if not data:
        return "_WSA-Enlil data unavailable_\n\n<sub>Source: [NASA DONKI WSA-Enlil](https://api.nasa.gov) — DEMO_KEY</sub>"

    out = [f"**WSA-Enlil Solar Wind Model Simulations — {len(data)} runs (last 14 days)**\n"]
    out.append("| Run Time | Estimated Shock | Impact Score | CME Count |")
    out.append("|:---------|:----------------|:-------------|----------:|")
    for sim in data[:8]:
        run_time = sim.get("simulationStartTime", "—")[:16]
        impact   = sim.get("estimatedShock1ArrivalTime", "None")
        if impact and impact != "None":
            impact = impact[:16]
        cmes     = len(sim.get("cmeInputs", []))
        score    = "Earth-directed" if sim.get("isEarthDirected") else "Not Earth-directed"
        out.append(f"| {run_time} | {impact or 'None'} | {score} | {cmes} |")

    out.append("\n<sub>Source: [NASA DONKI WSA-Enlil](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) — heliospheric solar wind model, DEMO_KEY</sub>")
    return "\n".join(out)

def get_satdb():
    """
    SatDB ETH Zurich: archives TLEs from CelesTrak hourly since 2013.
    Allows historical TLE lookup by NORAD ID and date range.
    No auth required.
    """
    # Query a few key satellites — latest TLE
    sats = [
        (25544, "ISS"),
        (48274, "Tiangong CSS"),
        (41335, "GOES-16"),
        (40697, "Sentinel-2A"),
        (37849, "Suomi NPP"),
        (39634, "Landsat 8"),
    ]
    out = ["#### SatDB ETH Zurich — TLE Archive (sampled)\n"]
    out.append("| Satellite | NORAD | TLE Epoch | TLE Line 1 (truncated) |")
    out.append("|:----------|------:|:----------|:----------------------|")
    for norad, name in sats:
        url  = f"https://satdb.ethz.ch/api/satellitedata/?norad-id={norad}&page-size=1&ordering=-datetime"
        data = jget(url)
        if not data or not data.get("results"): continue
        r   = data["results"][0]
        tle = r.get("norad_str", "")
        lines = [l for l in tle.splitlines() if l.strip()]
        l1   = lines[1][:40] + "..." if len(lines) > 1 else "—"
        epoch = lines[1][18:32].strip() if len(lines) > 1 else "—"
        out.append(f"| {name} | {norad} | {epoch} | `{l1}` |")
        time.sleep(0.2)

    out.append(f"\n_SatDB archives TLEs hourly from CelesTrak. Query by NORAD ID + date range for historical orbit reconstruction._")
    out.append(f"\n<sub>Source: [SatDB ETH Zurich](https://satdb.ethz.ch/api-documentation/) — TLE archive API, no auth</sub>")
    return "\n".join(out)

def get_keeptrack():
    """
    KeepTrack API: TLE + computed position for any NORAD object.
    Returns lat, lon, alt calculated from current TLE propagation.
    No auth, no rate limit stated. 63,000+ objects in catalog.
    """
    key_sats = [
        (25544,  "ISS"),
        (48274,  "Tiangong"),
        (41335,  "GOES-16"),
        (43013,  "NOAA-20"),
        (40697,  "Sentinel-2A"),
        (39634,  "Landsat 8"),
        (37849,  "Suomi NPP"),
        (43205,  "ICESat-2"),
    ]
    out = ["#### KeepTrack API — Live Satellite Positions\n"]
    out.append("| Satellite | NORAD | Lat | Lon | Alt (km) | Inc | Period |")
    out.append("|:----------|------:|----:|----:|---------:|----:|-------:|")

    import math
    MU = 398600.4418; RE = 6378.135

    for norad, name in key_sats:
        url  = f"https://api.keeptrack.space/v2/sat/{norad}"
        data = jget(url)
        if not data: continue
        try:
            tle1 = data.get("TLE_LINE_1", "")
            tle2 = data.get("TLE_LINE_2", "")
            if len(tle2) < 63: continue
            mm  = float(tle2[52:63])
            ecc = float("0." + tle2[26:33])
            inc = float(tle2[8:16])
            n   = mm * 2 * math.pi / 86400
            a   = (MU / n**2) ** (1/3)
            alt = round(a * (1 + ecc) - RE, 0)
            period = round(1440 / mm, 1)
            # KeepTrack doesn't return live lat/lon without propagation lib,
            # but returns TLE epoch which we can note
            epoch = tle1[18:32].strip() if tle1 else "—"
            out.append(f"| {name} | {norad} | TLE | epoch | {alt:.0f} | {inc:.1f}° | {period} min |")
        except: pass
        time.sleep(0.15)

    out.append(f"\n_KeepTrack covers 63,000+ objects. Use with [ootk](https://github.com/thkruz/ootk) to propagate real-time lat/lon/alt._")
    out.append(f"\n<sub>Source: [KeepTrack API](https://keeptrack.space/api) — no auth, 63k+ objects</sub>")
    return "\n".join(out)

def get_api_reference():
    return """
| # | API | Auth | Endpoint | Data |
|:-:|:----|:----:|:---------|:-----|
| 1 | **wheretheiss.at** | None | `api.wheretheiss.at/v1/satellites/25544` | ISS position, altitude, velocity, footprint |
| 2 | **Open Notify** | None | `api.open-notify.org/astros.json` | Humans in space, ISS crew |
| 3 | **Open Notify ISS Pass** | None | `api.open-notify.org/iss-pass.json?lat=&lon=` | ISS pass times over location |
| 4 | **CelesTrak GP** | None | `celestrak.org/NORAD/elements/gp.php?GROUP=&FORMAT=TLE` | All NORAD TLEs by category |
| 5 | **CelesTrak SATCAT** | None | `celestrak.org/pub/satcat.csv` | Full satellite catalog CSV |
| 6 | **CelesTrak SOCRATES** | None | `celestrak.org/SOCRATES/` | Conjunction/collision risk data |
| 7 | **TLE API** | None | `tle.ivanstanojevic.me/api/tle/?search=` | TLE search by name |
| 8 | **NOAA SWPC Solar Wind** | None | `services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json` | Speed, density, temp 2hr |
| 9 | **NOAA SWPC IMF** | None | `services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json` | Bz, Bt magnetic field |
| 10 | **NOAA SWPC Kp** | None | `services.swpc.noaa.gov/json/planetary_k_index_1m.json` | Geomagnetic Kp index |
| 11 | **NOAA SWPC X-ray** | None | `services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json` | Solar X-ray flux (GOES) |
| 12 | **NOAA SWPC Proton** | None | `services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json` | Proton flux |
| 13 | **NASA DONKI CME** | DEMO_KEY | `api.nasa.gov/DONKI/CME?startDate=&endDate=` | Coronal mass ejections |
| 14 | **NASA DONKI Flares** | DEMO_KEY | `api.nasa.gov/DONKI/FLR?startDate=&endDate=` | Solar flare events |
| 15 | **NASA DONKI Storms** | DEMO_KEY | `api.nasa.gov/DONKI/GST?startDate=&endDate=` | Geomagnetic storm events |
| 16 | **NASA NeoWs** | DEMO_KEY | `api.nasa.gov/neo/rest/v1/feed?start_date=` | Near Earth asteroid approaches |
| 17 | **NASA EPIC** | DEMO_KEY | `api.nasa.gov/EPIC/api/natural` | Earth photos from DSCOVR L1 |
| 18 | **NASA GIBS WMS** | None | `gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi` | 1000+ satellite imagery layers |
| 19 | **NASA FIRMS** | MAP_KEY | `firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_NOAA20_NRT/world/1` | MODIS+VIIRS fire detections |
| 20 | **NASA Mars Photos** | DEMO_KEY | `api.nasa.gov/mars-photos/api/v1/rovers/curiosity/latest_photos` | Curiosity/Perseverance photos |
| 21 | **NASA Exoplanet Archive** | None | `exoplanetarchive.ipac.caltech.edu/TAP/sync?query=` | Kepler/TESS discovered planets |
| 22 | **NASA APOD** | DEMO_KEY | `api.nasa.gov/planetary/apod` | Astronomy Picture of the Day |
| 23 | **NASA Earth Imagery** | DEMO_KEY | `api.nasa.gov/planetary/earth/imagery?lat=&lon=` | Landsat imagery by coordinate |
| 24 | **Space-Track.org** | Free account | `www.space-track.org/basicspacedata/query` | Full USSPACECOM catalog, debris |
| 25 | **N2YO API** | Free key | `api.n2yo.com/rest/v1/satellite/positions/{id}/{lat}/{lon}/{alt}/{seconds}` | Real-time satellite positions |
| 26 | **NASA POWER** | None | `power.larc.nasa.gov/api/temporal/daily/point` | Satellite-derived meteorological data |
| 27 | **Copernicus STAC** | Free | `catalogue.dataspace.copernicus.eu/stac` | Sentinel imagery STAC catalog |
| 28 | **Windy Satellite API** | None | `windy.com/webcams/map` | Live satellite-derived wind data |

<sub>DEMO_KEY = works without registration at 30 req/hr. MAP_KEY = 5000 transactions/10min. Free account = register once, unlimited.</sub>
"""


def main():
    print("Loading README.md...")
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    steps = [
        ("TIME",         get_timestamp),
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
        ("EARTHQUAKES",  get_earthquakes),
        ("NEOS",         get_neos),
        ("WEATHER",      get_weather_global),
        ("TEMP",         get_temperature_trend),
        ("CO2_ATMO",     get_co2),
        ("TICKER",       get_arxiv),
        ("FISHING",      get_fishing),
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
        ("TICKER",       get_arxiv),
        ("GITHUB",       get_github_trending),
        ("WIKI_TRENDS",  get_wikipedia_trending),
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
    print("\nGlobal Satellite Signal Dashboard updated.")


if __name__ == "__main__":
    main()