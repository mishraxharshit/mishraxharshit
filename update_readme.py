"""
update_readme.py
Fetches scientific data from free public APIs and injects it into README.md.

APIs used:
  - arXiv          : export.arxiv.org/api/query          (no key)
  - NASA APOD      : api.nasa.gov/planetary/apod         (free key)
  - NASA NeoWs     : api.nasa.gov/neo/rest/v1/feed       (free key)
  - USGS FDSN      : earthquake.usgs.gov/fdsnws/event/1  (no key)
  - NOAA SWPC      : services.swpc.noaa.gov              (no key)
"""

import os
import re
import json
import urllib.request
from datetime import datetime, timezone

import feedparser

NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def fetch_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "readme-updater/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  warn: fetch_json {url[:70]} — {e}")
        return None


# ── Data fetchers ─────────────────────────────────────────────────────────────

def fetch_arxiv():
    """Scrolling marquee of recent arXiv preprints (AI, ML, geophysics)."""
    print("fetching arXiv...")
    url = (
        "http://export.arxiv.org/api/query"
        "?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:physics.geo-ph"
        "&sortBy=submittedDate&sortOrder=descending&max_results=10"
    )
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            return "arXiv feed unavailable."

        items = []
        for e in feed.entries:
            title  = e.title.replace("\n", " ").strip()
            link   = e.link
            authors = e.get("authors", [])
            first  = authors[0]["name"].split(",")[0] if authors else "et al."
            items.append(f"<a href='{link}'>{title}</a> &mdash; {first}")

        sep    = " &nbsp; &bull; &nbsp; "
        ticker = sep.join(items)
        ts     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"<sub>Updated: {ts}</sub>\n\n"
            f'<marquee behavior="scroll" direction="left" scrollamount="4">{ticker}</marquee>'
        )
    except Exception as e:
        return f"arXiv error: {e}"


def fetch_nasa_apod():
    """Today's NASA Astronomy Picture of the Day."""
    print("fetching NASA APOD...")
    data = fetch_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}")
    if not data:
        return "NASA APOD unavailable."

    title  = data.get("title", "")
    blurb  = data.get("explanation", "")[:300].rsplit(" ", 1)[0] + "..."
    date   = data.get("date", "")
    mtype  = data.get("media_type", "image")
    img    = data.get("url", "")
    hd     = data.get("hdurl", img)

    if mtype == "image" and img:
        return (
            f"**{title}** &nbsp; <sub>{date}</sub>\n\n"
            f"<a href='{hd}'><img src='{img}' width='360' alt='{title}' /></a>\n\n"
            f"{blurb}\n\n"
            f"<sub><a href='https://apod.nasa.gov/apod/'>apod.nasa.gov</a></sub>"
        )
    else:
        return (
            f"**{title}** &nbsp; <sub>{date}</sub>\n\n"
            f"{blurb}\n\n"
            f"[View]({img}) &mdash; <sub><a href='https://apod.nasa.gov/apod/'>apod.nasa.gov</a></sub>"
        )


def fetch_usgs_earthquakes():
    """Five most significant earthquakes (M 4.5+) from the past 7 days."""
    print("fetching USGS earthquakes...")
    url  = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        "?format=geojson&minmagnitude=4.5&orderby=magnitude&limit=5"
    )
    data = fetch_json(url)
    if not data or not data.get("features"):
        return "No significant earthquakes (M 4.5+) in the past 7 days."

    ts    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows  = [
        f"<sub>Updated: {ts} &mdash; <a href='https://earthquake.usgs.gov'>earthquake.usgs.gov</a></sub>\n",
        "| Magnitude | Location | Depth | Time (UTC) |",
        "|-----------|----------|-------|------------|",
    ]
    for f in data["features"]:
        p     = f["properties"]
        g     = f["geometry"]["coordinates"]
        mag   = p.get("mag", "?")
        place = p.get("place", "Unknown")[:60]
        depth = f"{g[2]:.0f} km" if len(g) > 2 else "?"
        t     = datetime.fromtimestamp(p["time"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        link  = p.get("url", "#")
        rows.append(f"| M {mag} | [{place}]({link}) | {depth} | {t} |")

    return "\n".join(rows)


def fetch_space_weather():
    """Current solar wind speed and geomagnetic Kp index from NOAA SWPC."""
    print("fetching NOAA space weather...")
    sw   = fetch_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    kp   = fetch_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out  = [f"<sub>Updated: {ts} &mdash; <a href='https://www.swpc.noaa.gov'>swpc.noaa.gov</a></sub>\n"]

    if sw and len(sw) > 1:
        try:
            row     = sw[-1]
            speed   = float(row[2])
            density = float(row[1])
            if   speed > 700: label = "Very fast"
            elif speed > 500: label = "Fast"
            elif speed > 350: label = "Moderate"
            else:             label = "Slow"
            out.append(f"**Solar wind:** {speed:.0f} km/s ({label}) &nbsp; Density: {density:.1f} p/cm³")
        except (ValueError, IndexError):
            out.append("**Solar wind:** parse error")
    else:
        out.append("**Solar wind:** unavailable")

    if kp and len(kp) > 1:
        try:
            kp_val = float(kp[-1][1])
            if   kp_val >= 8: status = "Severe storm (G4–G5)"
            elif kp_val >= 6: status = "Strong storm (G3)"
            elif kp_val >= 5: status = "Moderate storm (G1–G2)"
            elif kp_val >= 4: status = "Active"
            else:             status = "Quiet"
            aurora = "  Aurora possible at high latitudes." if kp_val >= 5 else ""
            out.append(f"**Geomagnetic Kp:** {kp_val:.1f} — {status}.{aurora}")
        except (ValueError, IndexError):
            out.append("**Geomagnetic Kp:** parse error")
    else:
        out.append("**Geomagnetic Kp:** unavailable")

    return "\n\n".join(out)


def fetch_neo():
    """Near-Earth objects with close approaches today, from NASA CNEOS."""
    print("fetching NASA NEO...")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url   = (
        f"https://api.nasa.gov/neo/rest/v1/feed"
        f"?start_date={today}&end_date={today}&api_key={NASA_API_KEY}"
    )
    data = fetch_json(url)
    if not data:
        return "NASA NEO data unavailable."

    neos = data.get("near_earth_objects", {}).get(today, [])
    if not neos:
        return f"No notable close approaches on {today}."

    neos = sorted(
        neos,
        key=lambda x: float(
            x["close_approach_data"][0]["miss_distance"]["kilometers"]
        ) if x.get("close_approach_data") else float("inf")
    )[:5]

    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = [
        f"<sub>Updated: {ts} &mdash; <a href='https://cneos.jpl.nasa.gov/'>cneos.jpl.nasa.gov</a></sub>\n",
        "| Object | Est. diameter (m) | Miss distance | Speed (km/s) | Potentially hazardous |",
        "|--------|-------------------|---------------|--------------|----------------------|",
    ]
    for n in neos:
        name    = n.get("name", "?")
        hazard  = "Yes" if n.get("is_potentially_hazardous_asteroid") else "No"
        d       = n.get("estimated_diameter", {}).get("meters", {})
        dstr    = f"{d.get('estimated_diameter_min', 0):.0f}–{d.get('estimated_diameter_max', 0):.0f}"
        ca      = n.get("close_approach_data", [{}])[0]
        dist    = f"{float(ca.get('miss_distance', {}).get('kilometers', 0)):,.0f}"
        spd     = f"{float(ca.get('relative_velocity', {}).get('kilometers_per_second', 0)):.2f}"
        jpl     = n.get("nasa_jpl_url", "#")
        rows.append(f"| [{name}]({jpl}) | {dstr} | {dist} km | {spd} | {hazard} |")

    return "\n".join(rows)


# ── README injection ──────────────────────────────────────────────────────────

def inject(readme, start, end, content):
    pattern     = rf"{re.escape(start)}.*?{re.escape(end)}"
    replacement = f"{start}\n{content}\n{end}"
    result      = re.sub(pattern, replacement, readme, flags=re.DOTALL)
    if result == readme:
        print(f"  warn: marker not found — {start}")
    return result


def main():
    print("update_readme.py starting")

    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    readme = inject(readme, "<!-- ARXIV_TICKER_START -->", "<!-- ARXIV_TICKER_END -->", fetch_arxiv())
    readme = inject(readme, "<!-- NASA_APOD_START -->",    "<!-- NASA_APOD_END -->",    fetch_nasa_apod())
    readme = inject(readme, "<!-- USGS_START -->",         "<!-- USGS_END -->",         fetch_usgs_earthquakes())
    readme = inject(readme, "<!-- SWPC_START -->",         "<!-- SWPC_END -->",         fetch_space_weather())
    readme = inject(readme, "<!-- NEO_START -->",          "<!-- NEO_END -->",          fetch_neo())

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print("done — README.md updated.")


if __name__ == "__main__":
    main()