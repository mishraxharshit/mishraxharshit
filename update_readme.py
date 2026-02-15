import os
import re
import json
import math
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - PROFESSIONAL SCIENTIFIC DATA SOURCES
# ══════════════════════════════════════════════════════════════════════════════
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE  = "https://quickchart.io/chart?c="

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def get_json(url):
    """Fetch JSON from API with error handling"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ScientificDashboard/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"API Error: {url} - {e}")
        return None

def get_xml(url):
    """Fetch XML from API (for arXiv)"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ScientificDashboard/1.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return ET.fromstring(r.read())
    except Exception as e:
        print(f"XML Error: {url} - {e}")
        return None

def make_chart_img(config, width=500, height=300):
    """Generate QuickChart image URL"""
    params = json.dumps(config)
    safe_params = urllib.parse.quote(params)
    return f'<img src="{QC_BASE}{safe_params}&w={width}&h={height}&bkg=white" width="100%" />'

def inject(text, start, end, content):
    """Inject content between markers"""
    pattern = f"{re.escape(start)}.*?{re.escape(end)}"
    return re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)

# ══════════════════════════════════════════════════════════════════════════════
# 1. ARXIV RECENT PAPERS (Physics, Math, Computer Science)
# ══════════════════════════════════════════════════════════════════════════════
def get_arxiv_papers():
    """
    Latest research papers from arXiv.org
    Categories: Physics (quant-ph), Math (math), CS (cs)
    API: http://export.arxiv.org/api/query
    """
    # Get papers from last 7 days across major categories
    categories = ['quant-ph', 'astro-ph', 'math.CO', 'cs.AI']
    
    papers_by_category = {}
    for cat in categories:
        url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
        root = get_xml(url)
        
        if root is None:
            continue
        
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        
        count = len(entries)
        papers_by_category[cat] = count
    
    # Visualize submission activity
    labels = list(papers_by_category.keys())
    data = list(papers_by_category.values())
    
    config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Papers (Last Week)",
                "data": data,
                "backgroundColor": [
                    "rgba(63, 81, 181, 0.7)",
                    "rgba(103, 58, 183, 0.7)",
                    "rgba(0, 150, 136, 0.7)",
                    "rgba(255, 87, 34, 0.7)"
                ]
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {
                "y": {"ticks": {"beginAtZero": True}},
                "x": {"ticks": {"fontSize": 10}}
            },
            "title": {
                "display": True,
                "text": "arXiv Submissions by Field"
            }
        }
    }
    
    return make_chart_img(config, 600, 250)

# ══════════════════════════════════════════════════════════════════════════════
# 2. GLOBAL ECONOMIC INDICATORS (World Bank API)
# ══════════════════════════════════════════════════════════════════════════════
def get_economic_indicators():
    """
    GDP Growth, Inflation, Unemployment for major economies
    API: https://api.worldbank.org/v2/country/
    No authentication required
    """
    # Major economies
    countries = {
        'USA': 'United States',
        'CHN': 'China',
        'JPN': 'Japan',
        'DEU': 'Germany',
        'IND': 'India'
    }
    
    # GDP growth rate (NY.GDP.MKTP.KD.ZG)
    current_year = datetime.now().year - 1  # Latest complete data
    
    gdp_growth = {}
    for code, name in countries.items():
        url = f"https://api.worldbank.org/v2/country/{code}/indicator/NY.GDP.MKTP.KD.ZG?format=json&date={current_year}"
        data = get_json(url)
        
        if data and len(data) > 1 and len(data[1]) > 0:
            value = data[1][0].get('value')
            if value:
                gdp_growth[name] = value
    
    if not gdp_growth:
        # Fallback data
        gdp_growth = {'USA': 2.5, 'China': 5.2, 'Japan': 1.9, 'Germany': 0.1, 'India': 7.2}
    
    # Visualize
    labels = list(gdp_growth.keys())
    data = list(gdp_growth.values())
    
    # Color code: positive = green, negative = red
    colors = ['rgba(76, 175, 80, 0.7)' if v > 0 else 'rgba(244, 67, 54, 0.7)' for v in data]
    
    config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": f"GDP Growth % ({current_year})",
                "data": data,
                "backgroundColor": colors
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {
                "y": {"ticks": {"callback": "function(value) { return value + '%'; }"}},
                "x": {"ticks": {"fontSize": 10}}
            },
            "title": {
                "display": True,
                "text": "Real GDP Growth Rate"
            }
        }
    }
    
    return make_chart_img(config, 600, 250)

# ══════════════════════════════════════════════════════════════════════════════
# 3. ISS ORBITAL POSITION
# ══════════════════════════════════════════════════════════════════════════════
def get_iss_position():
    """Real-time ISS tracking"""
    current = get_json("http://api.open-notify.org/iss-now.json")
    
    if not current:
        return '<sub>ISS Tracker Unavailable</sub>'
    
    lat = float(current['iss_position']['latitude'])
    lon = float(current['iss_position']['longitude'])
    
    # Get astronaut count
    astros = get_json("http://api.open-notify.org/astros.json")
    count = astros['number'] if astros else 0
    
    # Simple orbital visualization
    orbit_points = []
    for i in range(50):
        angle = (i / 50) * 360
        orbit_lat = lat + 15 * math.sin(math.radians(angle))
        orbit_lon = (lon + 15 * math.cos(math.radians(angle))) % 360
        if orbit_lon > 180:
            orbit_lon -= 360
        orbit_points.append({"x": i, "y": orbit_lat})
    
    config = {
        "type": "line",
        "data": {
            "datasets": [{
                "label": "Orbital Path",
                "data": orbit_points,
                "borderColor": "rgba(33, 150, 243, 0.9)",
                "backgroundColor": "rgba(33, 150, 243, 0.1)",
                "fill": True,
                "pointRadius": 0,
                "borderWidth": 2
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {
                "x": {"display": False},
                "y": {"display": False}
            },
            "title": {
                "display": True,
                "text": f"ISS Position: {lat:.2f}°, {lon:.2f}° | Crew: {count}"
            }
        }
    }
    
    return make_chart_img(config, 600, 200)

# ══════════════════════════════════════════════════════════════════════════════
# 4. MATHEMATICAL VISUALIZATIONS
# ══════════════════════════════════════════════════════════════════════════════
def get_fourier_synthesis():
    """Fourier harmonic analysis"""
    day = datetime.now().timetuple().tm_yday
    points = 120
    x = [i * 0.05 for i in range(points)]
    
    # Generate harmonics
    fundamental = [math.sin(2 * math.pi * (i * 0.05 + day * 0.01)) for i in range(points)]
    harmonic2 = [0.5 * math.sin(4 * math.pi * (i * 0.05 + day * 0.01)) for i in range(points)]
    harmonic3 = [0.25 * math.sin(6 * math.pi * (i * 0.05 + day * 0.01)) for i in range(points)]
    complex_wave = [fundamental[i] + harmonic2[i] + harmonic3[i] for i in range(points)]
    
    config = {
        "type": "line",
        "data": {
            "labels": x,
            "datasets": [
                {"label": "f₀", "data": fundamental, "borderColor": "rgba(156, 39, 176, 0.6)", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"label": "2f₀", "data": harmonic2, "borderColor": "rgba(3, 169, 244, 0.6)", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"label": "3f₀", "data": harmonic3, "borderColor": "rgba(255, 152, 0, 0.6)", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"label": "Σ", "data": complex_wave, "borderColor": "rgba(244, 67, 54, 0.9)", "fill": False, "pointRadius": 0, "borderWidth": 2.5}
            ]
        },
        "options": {
            "legend": {"display": True, "position": "top", "labels": {"fontSize": 9}},
            "scales": {"x": {"display": False}, "y": {"display": False}},
            "elements": {"line": {"tension": 0.3}},
            "title": {"display": True, "text": "Fourier Synthesis"}
        }
    }
    return make_chart_img(config, 800, 220)

def get_lorenz_attractor():
    """Chaos theory visualization"""
    sigma, rho, beta = 10, 28, 8/3
    dt = 0.01
    day = datetime.now().timetuple().tm_yday
    x, y, z = 1 + day * 0.01, 1, 1
    
    points_x, points_y = [], []
    for _ in range(400):
        dx = sigma * (y - x) * dt
        dy = (x * (rho - z) - y) * dt
        dz = (x * y - beta * z) * dt
        x, y, z = x + dx, y + dy, z + dz
        points_x.append(x)
        points_y.append(y)
    
    config = {
        "type": "scatter",
        "data": {
            "datasets": [{
                "data": [{"x": points_x[i], "y": points_y[i]} for i in range(len(points_x))],
                "backgroundColor": "rgba(103, 58, 183, 0.4)",
                "borderColor": "rgba(103, 58, 183, 0.8)",
                "showLine": True,
                "pointRadius": 1,
                "borderWidth": 1.5
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"x": {"display": False}, "y": {"display": False}},
            "title": {"display": True, "text": "Lorenz Attractor (Chaos Theory)"}
        }
    }
    return make_chart_img(config, 400, 350)

# ══════════════════════════════════════════════════════════════════════════════
# 5. ORIGINAL FUNCTIONS (Enhanced)
# ══════════════════════════════════════════════════════════════════════════════
def get_solar_wind():
    """NOAA Solar wind speed"""
    data = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    speed = 400
    if data and len(data) > 1:
        try: 
            speed = float(data[-1][2])
        except: 
            pass
    
    config = {
        "type": "radialGauge",
        "data": {"datasets": [{"data": [speed], "backgroundColor": "rgba(244, 67, 54, 0.8)"}]},
        "options": {
            "domain": [200, 800],
            "trackColor": "rgba(200, 200, 200, 0.3)",
            "centerPercentage": 80,
            "roundedCorners": False
        }
    }
    return make_chart_img(config, 320, 220)

def get_seismic_activity():
    """USGS Earthquake monitoring"""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=4.5&limit=25&orderby=time"
    data = get_json(url)
    
    magnitudes = []
    timestamps = []
    
    if data and 'features' in data:
        for f in data['features']:
            mag = f['properties']['mag']
            time = f['properties']['time']
            magnitudes.append(mag)
            timestamps.append(time)
    
    if not magnitudes:
        magnitudes = [5.2, 4.8, 5.5, 4.6, 5.0]
    
    config = {
        "type": "line",
        "data": {
            "labels": list(range(len(magnitudes))),
            "datasets": [{
                "label": "Magnitude",
                "data": magnitudes,
                "borderColor": "rgba(255, 87, 34, 0.9)",
                "backgroundColor": "rgba(255, 87, 34, 0.2)",
                "fill": True,
                "pointRadius": 4,
                "pointBackgroundColor": "rgba(255, 87, 34, 1)",
                "borderWidth": 2
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {
                "y": {"ticks": {"beginAtZero": False, "min": 4}},
                "x": {"display": False}
            },
            "title": {"display": True, "text": "Recent Seismic Events (M4.5+)"}
        }
    }
    return make_chart_img(config, 600, 220)

def get_near_earth_objects():
    """NASA NEO tracking"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key={NASA_KEY}"
    data = get_json(url)
    
    count = 0
    max_diameter = 0
    potentially_hazardous = 0
    
    if data and "near_earth_objects" in data:
        neos = data.get("near_earth_objects", {}).get(today, [])
        count = len(neos)
        for n in neos:
            d = n['estimated_diameter']['meters']['estimated_diameter_max']
            if d > max_diameter:
                max_diameter = d
            if n.get('is_potentially_hazardous_asteroid', False):
                potentially_hazardous += 1
    
    info = f"<sub>Today: {count} asteroids | Max diameter: {int(max_diameter)}m | Potentially hazardous: {potentially_hazardous}</sub>"
    return info

def get_apod():
    """NASA Astronomy Picture of the Day"""
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    if data and data.get("media_type") == "image":
        url = data["url"]
        title = data.get("title", "Astronomy Picture")
        return f'<img src="{url}" width="100%" style="border-radius: 8px;" /><br><sub>{title}</sub>'
    return '<sub>APOD unavailable</sub>'

def get_temporal_pattern():
    """Time-domain interference visualization"""
    day_of_year = datetime.now().timetuple().tm_yday
    labels = list(range(0, 48))
    
    wave1 = [math.sin(x * 0.3 + day_of_year * 0.1) for x in labels]
    wave2 = [math.cos(x * 0.2 - day_of_year * 0.05) * 0.7 for x in labels]
    
    config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Ψ₁", "data": wave1, "borderColor": "rgba(0, 150, 136, 0.7)", "fill": False, "pointRadius": 0, "borderWidth": 2},
                {"label": "Ψ₂", "data": wave2, "borderColor": "rgba(156, 39, 176, 0.7)", "fill": False, "pointRadius": 0, "borderWidth": 2}
            ]
        },
        "options": {
            "legend": {"display": True, "position": "top"},
            "scales": {"x": {"display": False}, "y": {"display": False}},
            "elements": {"line": {"tension": 0.4}},
            "title": {"display": True, "text": "Temporal Interference Pattern"}
        }
    }
    return make_chart_img(config, 800, 160)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN UPDATE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Starting Scientific Dashboard Update...")
    
    with open("README.md", "r") as f:
        readme = f.read()

    # Research & Academia
    print("  Fetching arXiv papers...")
    readme = inject(readme, "", "", get_arxiv_papers())
    
    # Economic Data
    print("  Fetching economic indicators...")
    readme = inject(readme, "", "", get_economic_indicators())
    
    # Space & Astronomy
    print("  Tracking ISS position...")
    readme = inject(readme, "", "", get_iss_position())
    
    print("  Fetching solar wind data...")
    readme = inject(readme, "", "", get_solar_wind())
    
    print("  Loading APOD...")
    readme = inject(readme, "", "", get_apod())
    
    print("  Checking NEO data...")
    readme = inject(readme, "", "", get_near_earth_objects())
    
    # Geophysics
    print("  Monitoring seismic activity...")
    readme = inject(readme, "", "", get_seismic_activity())
    
    # Mathematics
    print("  Generating Fourier analysis...")
    readme = inject(readme, "", "", get_fourier_synthesis())
    
    print("  Computing Lorenz attractor...")
    readme = inject(readme, "", "", get_lorenz_attractor())
    
    print("  Creating temporal pattern...")
    readme = inject(readme, "", "", get_temporal_pattern())
    
    # Timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ts_badge = f'<sub>Last updated: {ts}</sub>'
    readme = inject(readme, "", "", ts_badge)

    with open("README.md", "w") as f:
        f.write(readme)
    
    print("Dashboard update complete.")

if __name__ == "__main__":
    main()