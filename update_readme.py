import os
import re
import json
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
QC_BASE  = "https://quickchart.io/chart?c="

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SciBot/1.0'})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except:
        return None

def make_chart_img(config, width=500, height=300):
    # Encodes JSON config for QuickChart
    params = json.dumps(config)
    safe_params = urllib.parse.quote(params)
    return f'<img src="{QC_BASE}{safe_params}&w={width}&h={height}&bkg=white" width="100%" />'

def inject(text, start, end, content):
    pattern = f"{re.escape(start)}.*?{re.escape(end)}"
    return re.sub(pattern, f"{start}\n{content}\n{end}", text, flags=re.DOTALL)

# ── 1. TIME & RESONANCE (Mathematical Visualization) ──────────────────────────
def get_resonance_graph():
    # Generates a 2D interference pattern based on current day of year
    day_of_year = datetime.now().timetuple().tm_yday
    
    labels = list(range(0, 24))
    data_sin = [math.sin(x + day_of_year) for x in labels]
    data_cos = [math.cos(x - day_of_year) * 0.5 for x in labels]
    
    config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Frequency A", "data": data_sin, "borderColor": "#4FC3F7", "fill": False, "pointRadius": 0, "borderWidth": 2},
                {"label": "Frequency B", "data": data_cos, "borderColor": "#9575CD", "fill": False, "pointRadius": 0, "borderWidth": 2}
            ]
        },
        "options": {
            "legend": {"display": False},
            "scales": {"x": {"display": False}, "y": {"display": False}},
            "elements": {"line": {"tension": 0.4}}
        }
    }
    return make_chart_img(config, 800, 150)

# ── 2. SOLAR WIND (Gauge Chart) ───────────────────────────────────────────────
def get_solar_gauge():
    # NOAA Solar Wind Data
    data = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    speed = 0
    if data and len(data) > 1:
        try: speed = float(data[-1][2])
        except: pass
    
    # Gauge Configuration
    config = {
        "type": "radialGauge",
        "data": {"datasets": [{"data": [speed], "backgroundColor": "#FF5252"}]},
        "options": {
            "domain": [200, 800],
            "trackColor": "#cccccc",
            "centerPercentage": 80,
            "roundedCorners": False
        }
    }
    return make_chart_img(config, 300, 200)

# ── 3. SEISMIC ACTIVITY (Scatter Plot) ────────────────────────────────────────
def get_seismic_graph():
    # USGS Earthquakes (M4.5+)
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=4.5&limit=20&orderby=time"
    data = get_json(url)
    
    points = []
    if data:
        for f in data['features']:
            mag = f['properties']['mag']
            # X axis is just index for simplicity in this visual
            points.append(mag)
            
    config = {
        "type": "line",
        "data": {
            "labels": list(range(len(points))),
            "datasets": [{
                "label": "Magnitude",
                "data": points,
                "borderColor": "#FF7043",
                "backgroundColor": "rgba(255, 112, 67, 0.2)",
                "fill": True
            }]
        },
        "options": {
            "legend": {"display": False},
            "scales": {
                "y": {"ticks": {"fontColor": "#666"}}, 
                "x": {"display": False}
            }
        }
    }
    return make_chart_img(config, 600, 200)

# ── 4. NEO HAZARD (Bar Chart) ─────────────────────────────────────────────────
def get_neo_graph():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key={NASA_KEY}"
    data = get_json(url)
    
    count = 0
    max_dia = 0
    if data:
        neos = data.get("near_earth_objects", {}).get(today, [])
        count = len(neos)
        for n in neos:
            d = n['estimated_diameter']['meters']['estimated_diameter_max']
            if d > max_dia: max_dia = d
            
    config = {
        "type": "progressBar",
        "data": {
            "datasets": [{
                "data": [count],
                "backgroundColor": "#66BB6A",
                "label": "Asteroid Count Today"
            }]
        },
        "options": {"domain": [0, 30]} # assuming max 30 per day for visual scale
    }
    # Simple workaround for progress bar visual
    return f'<img src="https://img.shields.io/badge/ASTEROIDS_TODAY-{count}-success?style=for-the-badge" /> <br> <img src="https://img.shields.io/badge/MAX_DIAMETER-{int(max_dia)}m-important?style=for-the-badge" />'

# ── 5. NASA APOD (Image Only) ─────────────────────────────────────────────────
def get_apod_img():
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    if data and data.get("media_type") == "image":
        return f'<img src="{data["url"]}" width="100%" style="border-radius: 10px;" />'
    return ""

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    with open("README.md", "r") as f:
        readme = f.read()

    # Generate content
    readme = inject(readme, "", "", get_resonance_graph())
    readme = inject(readme, "", "", get_solar_gauge())
    readme = inject(readme, "", "", get_apod_img())
    readme = inject(readme, "", "", get_seismic_graph())
    readme = inject(readme, "", "", get_neo_graph())
    
    # Timestamp badge
    ts = datetime.now(timezone.utc).strftime("%Y--%m--%d_%H:%M_UTC")
    ts_badge = f'<img src="https://img.shields.io/badge/UPDATED-{ts}-lightgrey?style=flat-square"/>'
    readme = inject(readme, "", "", ts_badge)

    with open("README.md", "w") as f:
        f.write(readme)

if __name__ == "__main__":
    main()