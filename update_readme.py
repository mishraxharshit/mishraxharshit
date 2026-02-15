import os
import re
import json
import math
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# CONFIGURATION
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE = "https://quickchart.io/chart?c="

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except:
        return None

def get_xml(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return ET.fromstring(r.read())
    except:
        return None

def make_chart(config, w=500, h=300):
    try:
        params = json.dumps(config)
        safe = urllib.parse.quote(params)
        return f'<img src="{QC_BASE}{safe}&w={w}&h={h}&bkg=white" width="100%" />'
    except:
        return ''

# FIX 1: inject() now requires real marker strings — no more empty-string calls.
def inject(text, tag, content):
    """Inject content between <!-- START_TAG --> and <!-- END_TAG --> markers."""
    start = f"<!-- START_{tag} -->"
    end   = f"<!-- END_{tag} -->"
    try:
        pattern = f"{re.escape(start)}.*?{re.escape(end)}"
        return re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)
    except:
        return text

def get_arxiv_ticker():
    categories = ['astro-ph', 'quant-ph', 'cs.AI', 'physics.comp-ph', 'math.CO']
    papers = []
    for cat in categories:
        url = (f"http://export.arxiv.org/api/query?search_query=cat:{cat}"
               f"&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending")
        root = get_xml(url)
        if not root:
            continue
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('atom:entry', ns)[:2]:
            title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')[:80]
            aid   = entry.find('atom:id', ns).text.split('/abs/')[-1]
            papers.append(
                f'<a href="https://arxiv.org/abs/{aid}" style="color:#fff;text-decoration:none">'
                f'<b>{cat.upper()}</b>: {title}</a>'
            )
    ticker = ' &nbsp;&bull;&nbsp; '.join(papers)
    return (
        '<div style="background:#102a43;color:white;padding:12px 0;overflow:hidden;'
        'font-family:sans-serif;font-size:13px;">'
        '<div style="white-space:nowrap;animation:scroll-left 60s linear infinite;">'
        f'{ticker} &nbsp;&bull;&nbsp; {ticker}'
        '</div></div>'
        '<style>@keyframes scroll-left{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}</style>'
    )

def get_global_earthquakes_map():
    url = ("https://earthquake.usgs.gov/fdsnws/event/1/query"
           "?format=geojson&minmagnitude=5.0&limit=40")
    data = get_json(url)
    points = []
    if data and 'features' in data:
        for f in data['features']:
            coords = f['geometry']['coordinates']
            points.append({"x": coords[0], "y": coords[1], "r": f['properties']['mag'] * 2})
    config = {
        "type": "bubble",
        "data": {"datasets": [{"data": points, "backgroundColor": "rgba(231,76,60,0.6)"}]},
        "options": {
            "title": {"display": True, "text": "GLOBAL SEISMIC EVENTS (M5+)"},
            "scales": {"x": {"min": -180, "max": 180}, "y": {"min": -90, "max": 90}}
        }
    }
    return make_chart(config, 800, 400)

# FIX 2: open-notify.org ISS API is defunct. Use wheretheiss.at instead.
def get_iss_orbit_visual():
    data = get_json("https://api.wheretheiss.at/v1/satellites/25544")
    if not data:
        return ''
    lat = float(data['latitude'])
    lon = float(data['longitude'])
    config = {
        "type": "scatter",
        "data": {"datasets": [{
            "label": "ISS",
            "data": [{"x": lon, "y": lat}],
            "pointRadius": 10,
            "pointBackgroundColor": "#3498db"
        }]},
        "options": {
            "title": {"display": True, "text": "ISS CURRENT COORDINATES"},
            "scales": {"x": {"min": -180, "max": 180}, "y": {"min": -90, "max": 90}}
        }
    }
    return make_chart(config, 500, 350)

def get_solar_wind_gauge():
    data  = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    speed = 400
    # Columns: [time, density, speed, temperature] — index 2 is correct for speed
    if data and len(data) > 1:
        try:
            speed = float(data[-1][2])
        except (TypeError, ValueError):
            pass
    config = {
        "type": "radialGauge",
        "data": {"datasets": [{"data": [speed], "backgroundColor": "#f1c40f"}]},
        "options": {"domain": [200, 800], "centerArea": {"text": f"{int(speed)} km/s"}}
    }
    return make_chart(config, 400, 300)

def get_climate_emissions():
    countries = {'CHN': 11500, 'USA': 5000, 'IND': 2900, 'RUS': 1700, 'JPN': 1100}
    config = {
        "type": "bar",
        "data": {
            "labels": list(countries.keys()),
            "datasets": [{"data": list(countries.values()), "backgroundColor": "#34495e"}]
        },
        "options": {"title": {"display": True, "text": "CO2 EMISSIONS (Mt/y)"}}
    }
    return make_chart(config, 600, 350)

# FIX 3: 'horizontalBar' was removed in Chart.js v3. Use 'bar' with indexAxis:'y'.
def get_renewable_energy():
    data = {'Iceland': 85, 'Norway': 71, 'Sweden': 60, 'Brazil': 46, 'Germany': 29}
    config = {
        "type": "bar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{"data": list(data.values()), "backgroundColor": "#2ecc71"}]
        },
        "options": {
            "indexAxis": "y",
            "title": {"display": True, "text": "RENEWABLE SHARE %"}
        }
    }
    return make_chart(config, 600, 350)

def get_pubmed_trends():
    fields = {'Cancer': 48, 'Neuro': 35, 'Immuno': 31, 'Genetics': 42}
    config = {
        "type": "doughnut",
        "data": {
            "labels": list(fields.keys()),
            "datasets": [{"data": list(fields.values()),
                          "backgroundColor": ["#e91e63", "#9c27b0", "#3f51b5", "#2196f3"]}]
        },
        "options": {"title": {"display": True, "text": "RESEARCH DISTRIBUTION"}}
    }
    return make_chart(config, 500, 400)

def get_temperature_trend():
    years = list(range(2010, 2024))
    temps = [0.70, 0.60, 0.64, 0.66, 0.74, 0.87, 0.99, 1.01, 0.92, 0.95, 1.02, 0.84, 1.04, 1.17]
    config = {
        "type": "line",
        "data": {
            "labels": years,
            "datasets": [{"data": temps, "borderColor": "#e74c3c", "fill": False}]
        },
        "options": {"title": {"display": True, "text": "GLOBAL TEMP ANOMALY (°C)"}}
    }
    return make_chart(config, 800, 300)

def get_fourier_waves():
    x = [round(i * 0.1, 2) for i in range(100)]
    y = [math.sin(v) + 0.5 * math.sin(2 * v) for v in x]
    config = {
        "type": "line",
        "data": {"labels": x, "datasets": [{"data": y, "borderColor": "#9b59b6", "pointRadius": 0}]},
        "options": {
            "title": {"display": True, "text": "FOURIER WAVE SYNTHESIS"},
            "scales": {"x": {"display": False}}
        }
    }
    return make_chart(config, 800, 200)

# FIX 4: Actual Lorenz attractor integration using Euler method (σ=10, ρ=28, β=8/3).
def get_lorenz_attractor():
    sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
    dt = 0.01
    x, y, z = 0.1, 0.0, 0.0
    points = []
    for _ in range(3000):
        dx = sigma * (y - x)
        dy = x * (rho - z) - y
        dz = x * y - beta * z
        x += dx * dt
        y += dy * dt
        z += dz * dt
        points.append({"x": round(x, 3), "y": round(z, 3)})  # X-Z plane view
    config = {
        "type": "scatter",
        "data": {"datasets": [{
            "data": points,
            "showLine": True,
            "borderColor": "#8e44ad",
            "pointRadius": 0,
            "borderWidth": 0.5
        }]},
        "options": {
            "title": {"display": True, "text": "LORENZ ATTRACTOR"},
            "scales": {"x": {"display": False}, "y": {"display": False}},
            "elements": {"line": {"tension": 0}}
        }
    }
    return make_chart(config, 400, 400)

def get_apod_visual():
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    if data and data.get("media_type") == "image":
        return f'<img src="{data["url"]}" width="100%" style="border-radius:5px;" />'
    return ''

def get_protein_visual():
    pdb = ["6LU7", "1BNA", "2HHB"][datetime.now().day % 3]
    return (f'<img src="https://cdn.rcsb.org/images/structures/{pdb.lower()}_assembly-1.jpeg"'
            f' width="100%" style="border-radius:5px;" />')

def main():
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    readme = inject(readme, "TIME",        f'<sub>Last Updated: {ts}</sub>')
    readme = inject(readme, "TICKER",      get_arxiv_ticker())
    readme = inject(readme, "EARTHQUAKES", get_global_earthquakes_map())
    readme = inject(readme, "ISS",         get_iss_orbit_visual())
    readme = inject(readme, "SOLAR",       get_solar_wind_gauge())
    readme = inject(readme, "CLIMATE",     get_climate_emissions())
    readme = inject(readme, "ENERGY",      get_renewable_energy())
    # FIX 5: Order corrected to match README (TEMP before PUBMED)
    readme = inject(readme, "TEMP",        get_temperature_trend())
    readme = inject(readme, "PUBMED",      get_pubmed_trends())
    readme = inject(readme, "FOURIER",     get_fourier_waves())
    readme = inject(readme, "LORENZ",      get_lorenz_attractor())
    readme = inject(readme, "APOD",        get_apod_visual())
    readme = inject(readme, "PROTEIN",     get_protein_visual())

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("Dashboard updated successfully.")

if __name__ == "__main__":
    main()