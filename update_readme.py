import os
import re
import json
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE = "https://quickchart.io/chart?c="

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_json(url):
    """Fetch JSON with timeout and error handling"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Warning: {url} failed - {e}")
        return None

def make_chart(config, w=500, h=300):
    """Generate chart URL"""
    try:
        params = json.dumps(config)
        safe = urllib.parse.quote(params)
        return f'<img src="{QC_BASE}{safe}&w={w}&h={h}&bkg=white" width="100%" />'
    except:
        return '<sub>Chart generation failed</sub>'

def inject(text, start, end, content):
    """Inject content between markers"""
    try:
        pattern = f"{re.escape(start)}.*?{re.escape(end)}"
        result = re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)
        if result == text:
            print(f"Warning: Markers not found: {start}")
        return result
    except Exception as e:
        print(f"Error in inject: {e}")
        return text

# ══════════════════════════════════════════════════════════════════════════════
# DATA FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_solar_wind():
    """NOAA Solar Wind"""
    data = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    speed = 400
    if data and len(data) > 1:
        try:
            speed = float(data[-1][2])
        except:
            pass
    
    config = {
        "type": "radialGauge",
        "data": {"datasets": [{"data": [speed], "backgroundColor": "rgb(244,67,54)"}]},
        "options": {"domain": [200, 800], "trackColor": "#ddd", "centerPercentage": 80}
    }
    return make_chart(config, 300, 200)

def get_seismic():
    """USGS Earthquakes"""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=4.5&limit=20&orderby=time"
    data = get_json(url)
    
    mags = []
    if data and 'features' in data:
        for f in data['features'][:20]:
            mags.append(f['properties']['mag'])
    
    if not mags:
        mags = [5.2, 4.8, 5.5, 4.6, 5.0, 4.9, 5.3]
    
    config = {
        "type": "line",
        "data": {
            "labels": list(range(len(mags))),
            "datasets": [{
                "data": mags,
                "borderColor": "rgb(255,87,34)",
                "backgroundColor": "rgba(255,87,34,0.2)",
                "fill": True
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"y": {"min": 4}, "x": {"display": False}}
        }
    }
    return make_chart(config, 600, 200)

def get_neo():
    """NASA Near Earth Objects"""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key={NASA_KEY}"
    data = get_json(url)
    
    count = 0
    max_d = 0
    
    if data and "near_earth_objects" in data:
        neos = data.get("near_earth_objects", {}).get(today, [])
        count = len(neos)
        for n in neos:
            d = n['estimated_diameter']['meters']['estimated_diameter_max']
            if d > max_d:
                max_d = d
    
    return f"<sub>Today: {count} asteroids | Max diameter: {int(max_d)}m</sub>"

def get_apod():
    """NASA APOD"""
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    if data and data.get("media_type") == "image":
        url = data["url"]
        title = data.get("title", "")
        return f'<img src="{url}" width="100%" /><br><sub>{title}</sub>'
    return '<sub>Image unavailable</sub>'

def get_iss():
    """ISS Position"""
    data = get_json("http://api.open-notify.org/iss-now.json")
    if not data:
        return '<sub>ISS data unavailable</sub>'
    
    lat = float(data['iss_position']['latitude'])
    lon = float(data['iss_position']['longitude'])
    
    astros = get_json("http://api.open-notify.org/astros.json")
    crew = astros['number'] if astros else 0
    
    points = []
    for i in range(40):
        angle = (i / 40) * 360
        y = lat + 12 * math.sin(math.radians(angle))
        points.append({"x": i, "y": y})
    
    config = {
        "type": "line",
        "data": {
            "datasets": [{
                "data": points,
                "borderColor": "rgb(33,150,243)",
                "fill": False,
                "pointRadius": 0
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"x": {"display": False}, "y": {"display": False}},
            "title": {"display": True, "text": f"ISS: {lat:.1f}°, {lon:.1f}° | Crew: {crew}"}
        }
    }
    return make_chart(config, 600, 180)

def get_fourier():
    """Fourier Synthesis"""
    day = datetime.now().timetuple().tm_yday
    n = 100
    x = [i * 0.06 for i in range(n)]
    
    f1 = [math.sin(2 * math.pi * (i * 0.06 + day * 0.01)) for i in range(n)]
    f2 = [0.5 * math.sin(4 * math.pi * (i * 0.06 + day * 0.01)) for i in range(n)]
    combined = [f1[i] + f2[i] for i in range(n)]
    
    config = {
        "type": "line",
        "data": {
            "labels": x,
            "datasets": [
                {"data": f1, "borderColor": "rgb(156,39,176)", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"data": f2, "borderColor": "rgb(3,169,244)", "fill": False, "pointRadius": 0, "borderWidth": 1.5},
                {"data": combined, "borderColor": "rgb(244,67,54)", "fill": False, "pointRadius": 0, "borderWidth": 2}
            ]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"x": {"display": False}, "y": {"display": False}}
        }
    }
    return make_chart(config, 800, 200)

def get_lorenz():
    """Lorenz Attractor"""
    sigma, rho, beta = 10, 28, 8/3
    dt = 0.01
    day = datetime.now().timetuple().tm_yday
    x, y, z = 1 + day * 0.01, 1, 1
    
    px, py = [], []
    for _ in range(300):
        dx = sigma * (y - x) * dt
        dy = (x * (rho - z) - y) * dt
        dz = (x * y - beta * z) * dt
        x, y, z = x + dx, y + dy, z + dz
        px.append(x)
        py.append(y)
    
    config = {
        "type": "scatter",
        "data": {
            "datasets": [{
                "data": [{"x": px[i], "y": py[i]} for i in range(len(px))],
                "backgroundColor": "rgba(103,58,183,0.3)",
                "borderColor": "rgb(103,58,183)",
                "showLine": True,
                "pointRadius": 1
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"x": {"display": False}, "y": {"display": False}}
        }
    }
    return make_chart(config, 400, 300)

def get_economics():
    """Economic Data"""
    # Using mock data since World Bank API can be slow
    data = {
        'USA': 2.5,
        'China': 5.2,
        'Japan': 1.9,
        'Germany': 0.1,
        'India': 7.2
    }
    
    labels = list(data.keys())
    values = list(data.values())
    colors = ['rgba(76,175,80,0.7)' if v > 0 else 'rgba(244,67,54,0.7)' for v in values]
    
    config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": values,
                "backgroundColor": colors
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"y": {"ticks": {"beginAtZero": True}}}
        }
    }
    return make_chart(config, 600, 220)

def get_arxiv():
    """arXiv Papers (simplified)"""
    # Mock data for reliability
    data = {
        'Physics': 45,
        'Math': 28,
        'CS': 62,
        'Astro': 31
    }
    
    config = {
        "type": "bar",
        "data": {
            "labels": list(data.keys()),
            "datasets": [{
                "data": list(data.values()),
                "backgroundColor": [
                    "rgba(63,81,181,0.7)",
                    "rgba(0,150,136,0.7)",
                    "rgba(255,87,34,0.7)",
                    "rgba(103,58,183,0.7)"
                ]
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"y": {"ticks": {"beginAtZero": True}}}
        }
    }
    return make_chart(config, 600, 220)

def get_temporal():
    """Temporal Pattern"""
    day = datetime.now().timetuple().tm_yday
    n = 40
    w1 = [math.sin(x * 0.3 + day * 0.1) for x in range(n)]
    w2 = [math.cos(x * 0.2 - day * 0.05) * 0.7 for x in range(n)]
    
    config = {
        "type": "line",
        "data": {
            "datasets": [
                {"data": w1, "borderColor": "rgb(0,150,136)", "fill": False, "pointRadius": 0},
                {"data": w2, "borderColor": "rgb(156,39,176)", "fill": False, "pointRadius": 0}
            ]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"x": {"display": False}, "y": {"display": False}}
        }
    }
    return make_chart(config, 800, 150)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Starting update...")
    
    try:
        with open("README.md", "r", encoding='utf-8') as f:
            readme = f.read()
    except FileNotFoundError:
        print("ERROR: README.md not found!")
        return
    
    # Update each section
    print("Updating sections...")
    readme = inject(readme, "<!-- START_ARXIV -->", "<!-- END_ARXIV -->", get_arxiv())
    readme = inject(readme, "<!-- START_ECONOMICS -->", "<!-- END_ECONOMICS -->", get_economics())
    readme = inject(readme, "<!-- START_ISS -->", "<!-- END_ISS -->", get_iss())
    readme = inject(readme, "<!-- START_SOLAR -->", "<!-- END_SOLAR -->", get_solar_wind())
    readme = inject(readme, "<!-- START_APOD -->", "<!-- END_APOD -->", get_apod())
    readme = inject(readme, "<!-- START_NEO -->", "<!-- END_NEO -->", get_neo())
    readme = inject(readme, "<!-- START_SEISMIC -->", "<!-- END_SEISMIC -->", get_seismic())
    readme = inject(readme, "<!-- START_FOURIER -->", "<!-- END_FOURIER -->", get_fourier())
    readme = inject(readme, "<!-- START_LORENZ -->", "<!-- END_LORENZ -->", get_lorenz())
    readme = inject(readme, "<!-- START_TEMPORAL -->", "<!-- END_TEMPORAL -->", get_temporal())
    
    # Timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    readme = inject(readme, "<!-- START_TIMESTAMP -->", "<!-- END_TIMESTAMP -->", f"<sub>Last updated: {ts}</sub>")
    
    try:
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(readme)
        print("Update completed successfully!")
    except Exception as e:
        print(f"ERROR writing file: {e}")

if __name__ == "__main__":
    main()