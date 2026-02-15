import os
import re
import json
import math
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE = "https://quickchart.io/chart?c="

def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except: return None

def get_xml(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return ET.fromstring(r.read())
    except: return None

def make_chart(config, w=500, h=300):
    try:
        params = json.dumps(config)
        safe = urllib.parse.quote(params)
        return f'<img src="{QC_BASE}{safe}&w={w}&h={h}&bkg=white" width="100%" />'
    except: return ''

def inject(text, start, end, content):
    try:
        pattern = f"{re.escape(start)}.*?{re.escape(end)}"
        return re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)
    except: return text

# ══════════════════════════════════════════════════════════════════════════════
# ARXIV NEWS TICKER - ANIMATED STRIP
# ══════════════════════════════════════════════════════════════════════════════
def get_arxiv_ticker():
    """Animated news ticker like CNN/BBC"""
    categories = ['astro-ph', 'quant-ph', 'cs.AI', 'physics.comp-ph', 'math.CO', 'q-bio']
    papers = []
    
    for cat in categories:
        url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending"
        root = get_xml(url)
        if not root: continue
        
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('atom:entry', ns)[:2]:
            title = entry.find('atom:title', ns)
            arxiv_id = entry.find('atom:id', ns)
            if title is not None and arxiv_id is not None:
                t = title.text.strip().replace('\n', ' ')[:90]
                aid = arxiv_id.text.split('/abs/')[-1]
                papers.append(f'<a href="https://arxiv.org/abs/{aid}" style="color:#fff;text-decoration:none"><b>{cat.upper()}</b>: {t}</a>')
    
    if not papers:
        papers = ['<b>ARXIV</b>: Loading latest research papers...']
    
    ticker = ' &nbsp;•&nbsp; '.join(papers)
    
    return f'''<div style="background: linear-gradient(90deg, #1a237e 0%, #0d47a1 100%); color: white; padding: 12px 0; overflow: hidden; font-family: 'Arial', sans-serif; font-size: 14px; font-weight: 500; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
<div style="white-space: nowrap; animation: scroll-left 60s linear infinite;">
{ticker} &nbsp;•&nbsp; {ticker}
</div>
</div>
<style>
@keyframes scroll-left {{
  0% {{ transform: translateX(0); }}
  100% {{ transform: translateX(-50%); }}
}}
</style>'''

# ══════════════════════════════════════════════════════════════════════════════
# VISUAL GRAPHS - NO TEXT EXPLANATIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_global_earthquakes_map():
    """World map with earthquake bubbles"""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=5.0&limit=40&orderby=time"
    data = get_json(url)
    
    lats, lons, mags = [], [], []
    if data and 'features' in data:
        for f in data['features'][:40]:
            coords = f['geometry']['coordinates']
            lons.append(coords[0])
            lats.append(coords[1])
            mags.append(f['properties']['mag'])
    
    if not lats:
        lats = [35.7, 40.7, -33.9, 51.5, 19.4, -15.8, 59.9]
        lons = [139.7, -74.0, 151.2, -0.1, -99.1, -47.9, 10.7]
        mags = [6.2, 5.5, 5.8, 5.3, 6.0, 5.7, 5.4]
    
    # World map scatter
    points = [{"x": lons[i], "y": lats[i], "r": mags[i] * 3} for i in range(len(lats))]
    
    config = {
        "type": "bubble",
        "data": {
            "datasets": [{
                "data": points,
                "backgroundColor": "rgba(244, 67, 54, 0.7)",
                "borderColor": "rgba(244, 67, 54, 1)",
                "borderWidth": 2
            }]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "GLOBAL SEISMIC ACTIVITY", "fontSize": 16, "fontColor": "#333"},
            "scales": {
                "x": {"ticks": {"min": -180, "max": 180}, "gridLines": {"color": "rgba(0,0,0,0.1)"}},
                "y": {"ticks": {"min": -90, "max": 90}, "gridLines": {"color": "rgba(0,0,0,0.1)"}}
            }
        }
    }
    return make_chart(config, 800, 400)

def get_solar_wind_gauge():
    """Big gauge for solar wind"""
    data = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    speed = 400
    if data and len(data) > 1:
        try: speed = float(data[-1][2])
        except: pass
    
    config = {
        "type": "radialGauge",
        "data": {"datasets": [{"data": [speed], "backgroundColor": ["#FF5252", "#FFC107", "#4CAF50"]}]},
        "options": {
            "domain": [200, 800],
            "trackColor": "rgba(200, 200, 200, 0.3)",
            "centerPercentage": 75,
            "roundedCorners": True,
            "centerArea": {
                "text": f"{int(speed)} km/s",
                "fontSize": 28,
                "fontColor": "#333"
            }
        }
    }
    return make_chart(config, 400, 300)

def get_iss_orbit_visual():
    """ISS orbital path visualization"""
    data = get_json("http://api.open-notify.org/iss-now.json")
    if not data: return ''
    
    lat = float(data['iss_position']['latitude'])
    lon = float(data['iss_position']['longitude'])
    
    # Generate orbital path
    orbit = []
    for i in range(100):
        angle = (i / 100) * 360
        o_lat = lat + 20 * math.sin(math.radians(angle + lon))
        o_lon = lon + 30 * math.cos(math.radians(angle))
        orbit.append({"x": o_lon, "y": o_lat})
    
    config = {
        "type": "scatter",
        "data": {
            "datasets": [
                {
                    "label": "Orbit",
                    "data": orbit,
                    "showLine": True,
                    "fill": False,
                    "borderColor": "rgba(33, 150, 243, 0.6)",
                    "pointRadius": 0,
                    "borderWidth": 3
                },
                {
                    "label": "ISS",
                    "data": [{"x": lon, "y": lat}],
                    "pointRadius": 12,
                    "pointBackgroundColor": "#FF5252",
                    "pointBorderColor": "#fff",
                    "pointBorderWidth": 3
                }
            ]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "ISS ORBITAL POSITION", "fontSize": 16},
            "scales": {
                "x": {"ticks": {"min": -180, "max": 180}},
                "y": {"ticks": {"min": -90, "max": 90}}
            }
        }
    }
    return make_chart(config, 700, 400)

def get_climate_emissions():
    """CO2 emissions bar chart"""
    countries = {
        'CHN': 11500, 'USA': 5000, 'IND': 2900, 'RUS': 1700, 
        'JPN': 1100, 'DEU': 680, 'IRN': 780, 'SAU': 620
    }
    
    config = {
        "type": "bar",
        "data": {
            "labels": list(countries.keys()),
            "datasets": [{
                "data": list(countries.values()),
                "backgroundColor": [
                    "#D32F2F", "#E64A19", "#F57C00", "#FBC02D",
                    "#AFB42B", "#689F38", "#00796B", "#0097A7"
                ]
            }]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "CO₂ EMISSIONS (Mt/year)", "fontSize": 16},
            "scales": {
                "y": {"ticks": {"beginAtZero": True}},
                "x": {"ticks": {"fontSize": 12}}
            }
        }
    }
    return make_chart(config, 700, 350)

def get_renewable_energy():
    """Renewable energy horizontal bars"""
    countries = {
        'Iceland': 85, 'Norway': 71, 'Sweden': 60, 'Brazil': 46,
        'Canada': 38, 'Germany': 29, 'USA': 22, 'China': 16, 'India': 11
    }
    
    colors = ['#4CAF50' if v > 50 else '#FFC107' if v > 30 else '#FF9800' if v > 15 else '#F44336' for v in countries.values()]
    
    config = {
        "type": "horizontalBar",
        "data": {
            "labels": list(countries.keys()),
            "datasets": [{"data": list(countries.values()), "backgroundColor": colors}]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "RENEWABLE ENERGY %", "fontSize": 16},
            "scales": {
                "x": {"ticks": {"min": 0, "max": 100}},
                "y": {"ticks": {"fontSize": 11}}
            }
        }
    }
    return make_chart(config, 700, 350)

def get_pubmed_trends():
    """Medical research activity"""
    fields = {
        'Cancer': 48000, 'Neuroscience': 35000, 'Immunology': 31000,
        'Genetics': 42000, 'Cardiology': 28000, 'Virology': 25000
    }
    
    config = {
        "type": "doughnut",
        "data": {
            "labels": list(fields.keys()),
            "datasets": [{
                "data": list(fields.values()),
                "backgroundColor": [
                    "#E91E63", "#9C27B0", "#3F51B5",
                    "#2196F3", "#00BCD4", "#009688"
                ]
            }]
        },
        "options": {
            "legend": {"position": "right", "labels": {"fontSize": 11}},
            "title": {"display": True, "text": "PUBMED PUBLICATIONS", "fontSize": 16}
        }
    }
    return make_chart(config, 600, 300)

def get_temperature_trend():
    """Global temperature anomaly"""
    years = list(range(2000, 2024))
    temps = [0.39, 0.52, 0.61, 0.60, 0.53, 0.67, 0.61, 0.64, 
             0.53, 0.64, 0.70, 0.60, 0.64, 0.66, 0.74, 0.87,
             0.99, 1.01, 0.92, 0.95, 1.02, 0.84, 1.04, 1.17]
    
    config = {
        "type": "line",
        "data": {
            "labels": years,
            "datasets": [{
                "data": temps,
                "borderColor": "#F44336",
                "backgroundColor": "rgba(244, 67, 54, 0.2)",
                "fill": True,
                "pointRadius": 4,
                "borderWidth": 3
            }]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "TEMPERATURE ANOMALY (°C)", "fontSize": 16},
            "scales": {
                "y": {"ticks": {"min": 0, "max": 1.5}},
                "x": {"ticks": {"fontSize": 10}}
            }
        }
    }
    return make_chart(config, 700, 300)

def get_fourier_waves():
    """Beautiful wave synthesis"""
    day = datetime.now().timetuple().tm_yday
    n = 120
    x = [i * 0.05 for i in range(n)]
    
    f1 = [math.sin(2 * math.pi * (i * 0.05 + day * 0.01)) for i in range(n)]
    f2 = [0.5 * math.sin(4 * math.pi * (i * 0.05 + day * 0.01)) for i in range(n)]
    f3 = [0.25 * math.sin(6 * math.pi * (i * 0.05 + day * 0.01)) for i in range(n)]
    combined = [f1[i] + f2[i] + f3[i] for i in range(n)]
    
    config = {
        "type": "line",
        "data": {
            "labels": x,
            "datasets": [
                {"data": f1, "borderColor": "#9C27B0", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"data": f2, "borderColor": "#2196F3", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"data": f3, "borderColor": "#4CAF50", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"data": combined, "borderColor": "#F44336", "fill": False, "pointRadius": 0, "borderWidth": 3}
            ]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "FOURIER SYNTHESIS", "fontSize": 16},
            "scales": {"x": {"display": False}, "y": {"display": False}}
        }
    }
    return make_chart(config, 800, 250)

def get_lorenz_attractor():
    """Chaos visualization"""
    sigma, rho, beta = 10, 28, 8/3
    dt = 0.01
    day = datetime.now().timetuple().tm_yday
    x, y, z = 1 + day * 0.01, 1, 1
    
    px, py = [], []
    for _ in range(400):
        dx, dy, dz = sigma * (y - x) * dt, (x * (rho - z) - y) * dt, (x * y - beta * z) * dt
        x, y, z = x + dx, y + dy, z + dz
        px.append(x)
        py.append(y)
    
    config = {
        "type": "scatter",
        "data": {
            "datasets": [{
                "data": [{"x": px[i], "y": py[i]} for i in range(len(px))],
                "backgroundColor": "rgba(156, 39, 176, 0.4)",
                "borderColor": "#9C27B0",
                "showLine": True,
                "pointRadius": 1,
                "borderWidth": 1.5
            }]
        },
        "options": {
            "legend": {"display": False},
            "title": {"display": True, "text": "LORENZ ATTRACTOR", "fontSize": 16},
            "scales": {"x": {"display": False}, "y": {"display": False}}
        }
    }
    return make_chart(config, 500, 400)

def get_apod_visual():
    """NASA image - pure visual"""
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    if data and data.get("media_type") == "image":
        return f'<img src="{data["url"]}" width="100%" style="border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />'
    return ''

def get_protein_visual():
    """Protein structure - pure image"""
    proteins = ["6LU7", "1BNA", "2HHB", "1GFL", "3I40", "1MSL", "1CRN"]
    day = datetime.now().timetuple().tm_yday
    pdb = proteins[day % len(proteins)]
    img = f"https://cdn.rcsb.org/images/structures/{pdb.lower()}_assembly-1.jpeg"
    return f'<img src="{img}" width="100%" style="border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />'

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Building VISUAL dashboard...")
    
    try:
        with open("README.md", "r", encoding='utf-8') as f:
            readme = f.read()
    except:
        print("ERROR: README.md not found!")
        return
    
    # ANIMATED NEWS TICKER
    readme = inject(readme, "<!-- START_TICKER -->", "<!-- END_TICKER -->", get_arxiv_ticker())
    
    # VISUAL GRAPHS
    readme = inject(readme, "<!-- START_EARTHQUAKES -->", "<!-- END_EARTHQUAKES -->", get_global_earthquakes_map())
    readme = inject(readme, "<!-- START_ISS -->", "<!-- END_ISS -->", get_iss_orbit_visual())
    readme = inject(readme, "<!-- START_SOLAR -->", "<!-- END_SOLAR -->", get_solar_wind_gauge())
    readme = inject(readme, "<!-- START_CLIMATE -->", "<!-- END_CLIMATE -->", get_climate_emissions())
    readme = inject(readme, "<!-- START_ENERGY -->", "<!-- END_ENERGY -->", get_renewable_energy())
    readme = inject(readme, "<!-- START_PUBMED -->", "<!-- END_PUBMED -->", get_pubmed_trends())
    readme = inject(readme, "<!-- START_TEMP -->", "<!-- END_TEMP -->", get_temperature_trend())
    readme = inject(readme, "<!-- START_FOURIER -->", "<!-- END_FOURIER -->", get_fourier_waves())
    readme = inject(readme, "<!-- START_LORENZ -->", "<!-- END_LORENZ -->", get_lorenz_attractor())
    readme = inject(readme, "<!-- START_APOD -->", "<!-- END_APOD -->", get_apod_visual())
    readme = inject(readme, "<!-- START_PROTEIN -->", "<!-- END_PROTEIN -->", get_protein_visual())
    
    # Minimal timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    readme = inject(readme, "<!-- START_TIME -->", "<!-- END_TIME -->", f'<sub>{ts}</sub>')
    
    try:
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(readme)
        print("✓ Visual dashboard updated!")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()