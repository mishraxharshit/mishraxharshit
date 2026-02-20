import os
import re
import json
import math
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE  = "https://quickchart.io/chart?c="
DARK_BG  = "%230D1117"   # URL-encoded #0D1117 — GitHub dark background

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except:
        return None

def get_xml(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return ET.fromstring(r.read())
    except:
        return None

def make_chart(config, w=600, h=300):
    """Render chart via QuickChart with dark background."""
    try:
        params = json.dumps(config, separators=(",", ":"))
        safe   = urllib.parse.quote(params)
        return f'<img src="{QC_BASE}{safe}&w={w}&h={h}&bkg={DARK_BG}" width="100%" />'
    except:
        return ""

def inject(text, tag, content):
    """Replace content between <!-- START_TAG --> and <!-- END_TAG -->."""
    start   = f"<!-- START_{tag} -->"
    end     = f"<!-- END_{tag} -->"
    pattern = f"{re.escape(start)}.*?{re.escape(end)}"
    try:
        return re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)
    except:
        return text

# ── Shared dark-theme config builders ─────────────────────────────────────────
def _title(text):
    return {"display": True, "text": text, "fontColor": "#E0E0E0", "fontSize": 14}

def _legend():
    return {"labels": {"fontColor": "#B0B0B0"}}

def _axes(x_label="", y_label="", x_min=None, x_max=None, y_min=None, y_max=None):
    x = {
        "ticks":     {"fontColor": "#B0B0B0"},
        "gridLines": {"color": "rgba(255,255,255,0.07)"},
        "scaleLabel":{"display": bool(x_label), "labelString": x_label, "fontColor": "#9E9E9E"}
    }
    y = {
        "ticks":     {"fontColor": "#B0B0B0"},
        "gridLines": {"color": "rgba(255,255,255,0.07)"},
        "scaleLabel":{"display": bool(y_label), "labelString": y_label, "fontColor": "#9E9E9E"}
    }
    if x_min is not None: x["ticks"]["min"] = x_min
    if x_max is not None: x["ticks"]["max"] = x_max
    if y_min is not None: y["ticks"]["min"] = y_min
    if y_max is not None: y["ticks"]["max"] = y_max
    return {"xAxes": [x], "yAxes": [y]}

# ── LIVE RESEARCH FEED ────────────────────────────────────────────────────────
def get_arxiv_ticker():
    """
    Markdown table of latest arXiv papers — auto-updates every run.
    GitHub strips CSS/JS so markdown table is the only reliable approach.
    """
    categories = ["astro-ph", "quant-ph", "cs.AI", "econ.GN", "q-bio.NC"]
    papers = []
    for cat in categories:
        url = (f"http://export.arxiv.org/api/query?search_query=cat:{cat}"
               f"&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending")
        root = get_xml(url)
        if not root:
            continue
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:2]:
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")[:78]
            aid   = entry.find("atom:id",    ns).text.split("/abs/")[-1]
            papers.append((cat.upper(), title, aid))

    if not papers:
        return "_No recent papers fetched._"

    BADGE = {
        "ASTRO-PH": "🔵 Astrophysics",
        "QUANT-PH":  "🟣 Quantum Physics",
        "CS.AI":     "🟢 AI / CS",
        "ECON.GN":   "🟡 Economics",
        "Q-BIO.NC":  "🔴 Neuroscience",
    }
    rows = ["| # | Field | Latest Paper (auto-updated every 6 hrs) |",
            "|:-:|:------|:-----------------------------------------|"]
    for i, (label, title, aid) in enumerate(papers, 1):
        badge = BADGE.get(label, f"⚪ {label}")
        link  = f"[{title}](https://arxiv.org/abs/{aid})"
        rows.append(f"| {i} | {badge} | {link} |")
    return "\n".join(rows)

# ── EARTH & SPACE ─────────────────────────────────────────────────────────────
def get_global_earthquakes_map():
    data   = get_json("https://earthquake.usgs.gov/fdsnws/event/1/query"
                      "?format=geojson&minmagnitude=5.0&limit=40")
    points = []
    if data and "features" in data:
        for f in data["features"]:
            c = f["geometry"]["coordinates"]
            m = f["properties"]["mag"]
            points.append({"x": round(c[0], 2), "y": round(c[1], 2),
                           "r": round(m * 2.5, 1)})
    config = {
        "type": "bubble",
        "data": {"datasets": [{
            "label": "Earthquake  (bubble size ∝ magnitude)",
            "data":  points,
            "backgroundColor": "rgba(231,76,60,0.5)",
            "borderColor":     "rgba(231,76,60,0.85)",
            "borderWidth": 1
        }]},
        "options": {
            "title":  _title("🌋 Global Seismic Events — M 5.0+ (Last 40)"),
            "legend": _legend(),
            "scales": _axes(x_label="Longitude (°)", x_min=-180, x_max=180,
                            y_label="Latitude (°)",  y_min=-90,  y_max=90)
        }
    }
    return make_chart(config, 700, 350)

def get_iss_orbit_visual():
    data = get_json("https://api.wheretheiss.at/v1/satellites/25544")
    if not data:
        return ""
    lat = round(float(data["latitude"]),  2)
    lon = round(float(data["longitude"]), 2)
    config = {
        "type": "scatter",
        "data": {"datasets": [{
            "label": f"ISS Position — {lat}°N  {lon}°E",
            "data":  [{"x": lon, "y": lat}],
            "pointRadius": 12,
            "pointBackgroundColor": "#4FC3F7",
            "pointBorderColor":     "#ffffff",
            "pointBorderWidth": 2
        }]},
        "options": {
            "title":  _title("🛰️ ISS Live Position"),
            "legend": _legend(),
            "scales": _axes(x_label="Longitude (°)", x_min=-180, x_max=180,
                            y_label="Latitude (°)",  y_min=-90,  y_max=90)
        }
    }
    return make_chart(config, 420, 300)

def get_solar_wind_gauge():
    """Doughnut-based gauge — reliable on QuickChart, radialGauge is not."""
    data  = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    speed = 400
    if data and len(data) > 1:
        try:
            speed = float(data[-1][2])
        except (TypeError, ValueError):
            pass
    speed = int(speed)

    filled    = min(speed, 800)
    remainder = max(800 - filled, 0)
    color  = "#2ecc71" if speed < 400 else ("#f39c12" if speed < 600 else "#e74c3c")
    status = "Calm" if speed < 400 else ("Moderate" if speed < 600 else "⚠️ Storm Risk")

    config = {
        "type": "doughnut",
        "data": {
            "labels": [f"{speed} km/s — {status}", "Remaining range (800 km/s max)"],
            "datasets": [{
                "data":            [filled, remainder],
                "backgroundColor": [color, "rgba(255,255,255,0.06)"],
                "borderColor":     [color, "rgba(255,255,255,0.04)"],
                "borderWidth": 1
            }]
        },
        "options": {
            "title":             _title(f"💨 Solar Wind Speed — {speed} km/s"),
            "legend":            _legend(),
            "cutoutPercentage":  70,
            "rotation":         -3.14159,
            "circumference":     3.14159
        }
    }
    return make_chart(config, 900, 300)

# ── CLIMATE & ENERGY ──────────────────────────────────────────────────────────

# World Bank indicator helper
def _wb_fetch(indicator, iso_codes, fallback):
    """
    Fetch latest non-null value for each country from World Bank API.
    Returns dict {name: value} using most recent available year.
    Falls back to `fallback` dict if API fails.
    """
    codes = ";".join(iso_codes.values())
    url   = (f"https://api.worldbank.org/v2/country/{codes}/indicator/{indicator}"
             f"?format=json&mrv=5&per_page=50")
    data  = get_json(url)
    if not data or len(data) < 2 or not data[1]:
        return fallback, "fallback"
    # Build {iso: (name, value, date)} keeping latest non-null per country
    latest = {}
    for rec in data[1]:
        if rec.get("value") is None:
            continue
        iso  = rec["countryiso3code"]
        date = rec["date"]
        if iso not in latest or date > latest[iso][2]:
            latest[iso] = (rec["country"]["value"], rec["value"], date)
    result = {}
    year   = None
    for iso, name in iso_codes.items():
        short_name = name  # use our label, not WB's long name
        if iso in latest:
            result[short_name] = round(latest[iso][1], 2)
            year = latest[iso][2]
    if not result:
        return fallback, "fallback"
    return result, year

def get_climate_emissions():
    """CO₂ emissions — World Bank EN.ATM.CO2E.KT (latest available, ~2021-22)."""
    iso_codes = {"CHN": "China", "USA": "USA", "IND": "India",
                 "RUS": "Russia", "JPN": "Japan"}
    # Fallback values in million tonnes (kt → Mt ÷ 1000)
    fallback  = {"China": 11500, "USA": 5000, "India": 2900,
                 "Russia": 1700, "Japan": 1100}
    raw, year = _wb_fetch("EN.ATM.CO2E.KT", iso_codes, fallback)
    # Convert kt → million tonnes
    data = {k: round(v / 1000, 1) for k, v in raw.items()} if year != "fallback" else fallback
    label = f"CO₂ Emissions (Mt/year) — World Bank {year}"
    title_txt = f"🏭 CO₂ Emissions by Country ({year})"
    config = {
        "type": "bar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "label": label,
                "data":  list(data.values()),
                "backgroundColor": ["#e74c3c","#3498db","#f39c12","#9b59b6","#1abc9c"]
            }]
        },
        "options": {
            "title":  _title(title_txt),
            "legend": _legend(),
            "scales": _axes(y_label="Million Tonnes CO₂ / year", y_min=0)
        }
    }
    return make_chart(config, 500, 300)

def get_renewable_energy():
    """Renewable electricity share — World Bank EG.ELC.RNEW.ZS (latest ~2021-22)."""
    iso_codes = {"ISL": "Iceland", "NOR": "Norway", "SWE": "Sweden",
                 "BRA": "Brazil",  "DEU": "Germany"}
    fallback  = {"Iceland": 85, "Norway": 71, "Sweden": 60, "Brazil": 46, "Germany": 29}
    data, year = _wb_fetch("EG.ELC.RNEW.ZS", iso_codes, fallback)
    label = f"Renewable electricity share (%) — World Bank {year}"
    title_txt = f"⚡ Renewable Energy Share — {year}"
    config = {
        "type": "horizontalBar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "label": label,
                "data":  list(data.values()),
                "backgroundColor": ["#1abc9c","#2ecc71","#27ae60","#f39c12","#3498db"]
            }]
        },
        "options": {
            "title":  _title(title_txt),
            "legend": _legend(),
            "scales": _axes(x_label="Share of total electricity (%)", x_min=0, x_max=100)
        }
    }
    return make_chart(config, 500, 300)

def get_temperature_trend():
    """
    NASA GISS global temperature anomaly — fetched live from GISS CSV.
    Covers 2010 to most recent available year (updated annually by NASA).
    Fallback: hardcoded data through 2024.
    """
    FALLBACK_YEARS = list(range(2010, 2025))
    FALLBACK_TEMPS = [0.70,0.60,0.64,0.66,0.74,0.87,
                      0.99,1.01,0.92,0.95,1.02,0.84,1.04,1.17,1.29]

    years, temps = FALLBACK_YEARS, FALLBACK_TEMPS
    try:
        url = ("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode(errors="ignore")
        lines = text.strip().splitlines()
        # Find header row — "Year,Jan,Feb,...,J-D" format
        header_idx = next((i for i, l in enumerate(lines) if l.startswith("Year")), None)
        if header_idx is not None:
            parsed_years, parsed_temps = [], []
            for line in lines[header_idx + 1:]:
                parts = line.split(",")
                if len(parts) < 14:
                    continue
                try:
                    yr  = int(parts[0])
                    jd  = parts[13].strip()  # J-D annual mean column
                    if yr >= 2010 and jd not in ("", "****", "***"):
                        parsed_years.append(yr)
                        parsed_temps.append(round(float(jd), 2))
                except (ValueError, IndexError):
                    continue
            if len(parsed_years) >= 5:
                years, temps = parsed_years, parsed_temps
    except Exception:
        pass  # use fallback silently

    latest_yr = years[-1] if years else 2024
    y_max = max(temps) + 0.15 if temps else 1.5
    config = {
        "type": "line",
        "data": {
            "labels": years,
            "datasets": [{
                "label": "Temperature anomaly vs 1951–1980 baseline (°C) — NASA GISS",
                "data":  temps,
                "borderColor":     "#e74c3c",
                "backgroundColor": "rgba(231,76,60,0.15)",
                "fill": True,
                "pointBackgroundColor": "#e74c3c",
                "pointRadius": 4
            }]
        },
        "options": {
            "title":  _title(f"🌡️ Global Temperature Anomaly 2010–{latest_yr} (NASA GISS)"),
            "legend": _legend(),
            "scales": _axes(x_label="Year", y_label="Anomaly (°C)",
                            y_min=0.4, y_max=round(y_max, 1))
        }
    }
    return make_chart(config, 900, 300)

# ── ECONOMICS ─────────────────────────────────────────────────────────────────
def get_gdp_growth():
    """GDP growth rate — World Bank NY.GDP.MKTP.KD.ZG, latest available year."""
    iso_codes = {"IND": "India",   "CHN": "China", "USA": "USA",
                 "DEU": "Germany", "GBR": "UK",    "JPN": "Japan",
                 "BRA": "Brazil",  "ZAF": "S.Africa"}
    fallback  = {"India": 6.3, "China": 5.2, "USA": 2.5,
                 "Germany": -0.3, "UK": 0.1, "Japan": 1.9,
                 "Brazil": 2.9, "S.Africa": 0.6}
    data, year = _wb_fetch("NY.GDP.MKTP.KD.ZG", iso_codes, fallback)
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in data.values()]
    vals   = [round(v, 2) for v in data.values()]
    y_min  = min(vals) - 0.5
    y_max  = max(vals) + 0.5
    config = {
        "type": "bar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "label": f"GDP Growth Rate (%) — World Bank {year}",
                "data":  vals,
                "backgroundColor": colors
            }]
        },
        "options": {
            "title":  _title(f"📈 GDP Growth Rate — Major Economies ({year})"),
            "legend": _legend(),
            "scales": _axes(y_label="Growth Rate (%)", y_min=round(y_min,1), y_max=round(y_max,1))
        }
    }
    return make_chart(config, 560, 320)

def get_inflation_chart():
    """
    CPI Inflation — World Bank FP.CPI.TOTL.ZG, latest available year.
    Falls back to IMF WEO JSON if WB data is stale.
    """
    iso_codes = {"ARG": "Argentina", "TUR": "Turkey",  "NGA": "Nigeria",
                 "BRA": "Brazil",    "USA": "USA",      "EMU": "EU",
                 "CHN": "China",     "JPN": "Japan"}
    # EU is not in WB as "EMU" individually — try EUU (European Union aggregate)
    iso_codes_wb = {k if k != "EMU" else "EUU": v for k, v in iso_codes.items()}
    fallback = {"Argentina": 133, "Turkey": 64, "Nigeria": 28,
                "Brazil": 5.1, "USA": 3.4, "EU": 5.4, "China": 0.2, "Japan": 3.3}
    data, year = _wb_fetch("FP.CPI.TOTL.ZG", iso_codes_wb, fallback)
    colors = ["#e74c3c" if v > 10 else ("#f39c12" if v > 5 else "#2ecc71")
              for v in data.values()]
    config = {
        "type": "horizontalBar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "label": f"Inflation Rate (%) — World Bank {year}",
                "data":  list(data.values()),
                "backgroundColor": colors
            }]
        },
        "options": {
            "title":  _title(f"💸 Inflation Rates ({year}) — World Bank CPI"),
            "legend": _legend(),
            "scales": _axes(x_label="Inflation Rate (%)", x_min=0)
        }
    }
    return make_chart(config, 560, 320)

def get_trade_balance():
    """
    Trade balance — World Bank BN.CAB.XOKA.CD (current account, USD).
    Closest publicly available proxy; mrv=5 to get latest non-null year.
    """
    iso_codes = {"CHN": "China",  "DEU": "Germany", "JPN": "Japan",
                 "USA": "USA",    "GBR": "UK",       "IND": "India"}
    fallback  = {"China": 823, "Germany": 224, "Japan": -9,
                 "USA": -778, "UK": -232, "India": -247}
    raw, year = _wb_fetch("BN.CAB.XOKA.CD", iso_codes, fallback)
    # Convert USD → USD Billion
    if year != "fallback":
        data = {k: round(v / 1e9, 1) for k, v in raw.items()}
    else:
        data = fallback
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in data.values()]
    config = {
        "type": "bar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "label": f"Current Account Balance (USD Billion) — World Bank {year}",
                "data":  list(data.values()),
                "backgroundColor": colors
            }]
        },
        "options": {
            "title":  _title(f"⚖️ Trade Balance — Major Economies ({year})"),
            "legend": _legend(),
            "scales": _axes(y_label="USD Billion")
        }
    }
    return make_chart(config, 900, 300)

# ── VISUAL DATA ───────────────────────────────────────────────────────────────
def get_apod_visual():
    """
    NASA APOD with video fallback and curated image fallback.
    Never returns empty — always shows something.
    """
    # DEMO_KEY rate limit: 30 req/hr. Real key use karo NASA_API_KEY secret se.
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}&thumbs=true")
    if data and "error" not in data and "code" not in data:
        media = data.get("media_type", "")
        title = data.get("title", "NASA APOD")
        date  = data.get("date", "")
        expl  = (data.get("explanation", "")[:220] + "…") if data.get("explanation") else ""

        if media == "image":
            url = data.get("hdurl") or data.get("url", "")
            if url:
                return (
                    f'<img src="{url}" width="100%" style="border-radius:6px;" />\n\n'
                    f'**{title}** &nbsp; _{date}_\n\n{expl}'
                )

        if media == "video":
            vurl  = data.get("url", "")
            # thumbs=true parameter se thumbnail milta hai video ke liye
            thumb = data.get("thumbnail_url", "")
            if thumb:
                return (
                    f'<img src="{thumb}" width="100%" style="border-radius:6px;" />\n\n'
                    f'▶️ **[{title} — Watch Video]({vurl})** &nbsp; _{date}_\n\n{expl}'
                )
            else:
                # Thumbnail nahi mila — sirf link dikhao
                return (
                    f'▶️ **[{title} — Watch on NASA]({vurl})** &nbsp; _{date}_\n\n{expl}\n\n'
                    f'_([Browse APOD Archive](https://apod.nasa.gov/apod/archivepix.html))_'
                )

    # Curated fallback — rotates by day-of-month
    # (API fail ho ya rate limit ho tab bhi kuch dikhega)
    fallbacks = [
        ("https://apod.nasa.gov/apod/image/2401/ArcticNight_Cobianchi_2048.jpg",
         "Arctic Night — Noctilucent clouds over Norway"),
        ("https://apod.nasa.gov/apod/image/2402/Horsehead_Webb_960.jpg",
         "Horsehead Nebula — James Webb Space Telescope"),
        ("https://apod.nasa.gov/apod/image/2312/NGC1232_Eye_1024.jpg",
         "NGC 1232 — A Grand Design Spiral Galaxy"),
    ]
    img_url, caption = fallbacks[datetime.now().day % len(fallbacks)]
    return (
        f'<img src="{img_url}" width="100%" style="border-radius:6px;" />\n\n'
        f'🌌 _{caption}_ &nbsp;([Browse APOD Archive](https://apod.nasa.gov/apod/archivepix.html))'
    )

def get_protein_visual():
    """Rotates between 3 well-known protein structures daily."""
    entries = [
        ("6LU7", "COVID-19 Main Protease"),
        ("1BNA", "B-DNA Double Helix"),
        ("2HHB", "Haemoglobin"),
    ]
    pdb, name = entries[datetime.now().day % len(entries)]
    return (
        f'<img src="https://cdn.rcsb.org/images/structures/{pdb.lower()}_assembly-1.jpeg"'
        f' width="100%" style="border-radius:6px;" />\n\n'
        f'🧬 **{name}** &nbsp; PDB: `{pdb}` &nbsp;'
        f'([View 3D Structure](https://www.rcsb.org/structure/{pdb}))'
    )

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    readme = inject(readme, "TIME",        f'<sub>⏱ Last Updated: {ts}</sub>')
    readme = inject(readme, "TICKER",      get_arxiv_ticker())
    readme = inject(readme, "EARTHQUAKES", get_global_earthquakes_map())
    readme = inject(readme, "ISS",         get_iss_orbit_visual())
    readme = inject(readme, "SOLAR",       get_solar_wind_gauge())
    readme = inject(readme, "CLIMATE",     get_climate_emissions())
    readme = inject(readme, "ENERGY",      get_renewable_energy())
    readme = inject(readme, "TEMP",        get_temperature_trend())
    readme = inject(readme, "GDP",         get_gdp_growth())
    readme = inject(readme, "INFLATION",   get_inflation_chart())
    readme = inject(readme, "TRADE",       get_trade_balance())
    readme = inject(readme, "APOD",        get_apod_visual())
    readme = inject(readme, "PROTEIN",     get_protein_visual())

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("Dashboard updated successfully.")

if __name__ == "__main__":
    main()