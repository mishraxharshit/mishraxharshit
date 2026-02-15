"""
update_readme.py

Pulls from 5 free, no-auth-needed APIs and injects data into README.md.
Run locally or via GitHub Actions.

APIs:
  arXiv      — export.arxiv.org/api/query           (no key, no limit)
  USGS       — earthquake.usgs.gov/fdsnws/event/1   (no key, no limit)
  NOAA SWPC  — services.swpc.noaa.gov               (no key, no limit)
  NASA APOD  — api.nasa.gov/planetary/apod          (free key or DEMO_KEY)
  NASA NEO   — api.nasa.gov/neo/rest/v1/feed        (same key)
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

import feedparser

# ── config ────────────────────────────────────────────────────────────────────

NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
HEADERS  = {"User-Agent": "github-readme-updater/2.0"}
TIMEOUT  = 20


# ── http ─────────────────────────────────────────────────────────────────────

def get_json(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {url[:80]}")
    except Exception as e:
        print(f"  ERR: {url[:80]} — {e}")
    return None


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── arXiv ─────────────────────────────────────────────────────────────────────

def section_arxiv():
    """Scrolling ticker + static table. No key, no rate limit."""
    print("arXiv...")
    url = (
        "https://export.arxiv.org/api/query"
        "?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:physics.geo-ph"
        "&sortBy=submittedDate&sortOrder=descending&max_results=8"
    )
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        err = f"arXiv parse error: {e}"
        return err, err

    if not feed.entries:
        err = "arXiv: no entries returned."
        return err, err

    ts = utc_now()

    # ticker — all 8
    links = " &nbsp;·&nbsp; ".join(
        f'<a href="{e.link}">{e.title.replace(chr(10)," ").strip()}</a>'
        for e in feed.entries
    )
    ticker = (
        f'<sub>Updated {ts}</sub><br>\n'
        f'<marquee scrollamount="4" direction="left">{links}</marquee>'
    )

    # table — top 5
    rows = [
        "| Title | Authors | Cat |",
        "|-------|---------|-----|",
    ]
    for e in feed.entries[:5]:
        title   = e.title.replace("\n", " ").strip()
        authors = e.get("authors", [])
        names   = ", ".join(a["name"].split(",")[0] for a in authors[:2])
        if len(authors) > 2:
            names += " et al."
        cat = e.get("tags", [{}])[0].get("term", "") if e.get("tags") else ""
        rows.append(f'| [{title}]({e.link}) | {names} | `{cat}` |')

    return ticker, "\n".join(rows)


# ── NASA APOD ─────────────────────────────────────────────────────────────────

def section_apod():
    """Full inline image + description. Free key, 30 req/hr on DEMO_KEY."""
    print("NASA APOD...")
    data = get_json(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    if not data:
        return "_NASA APOD unavailable — check NASA_API_KEY secret._"

    title = data.get("title", "")
    date  = data.get("date", "")
    expl  = data.get("explanation", "")
    mtype = data.get("media_type", "image")
    url   = data.get("url", "")
    hd    = data.get("hdurl", url)

    if mtype == "image" and url:
        return (
            f"**{title}** <sub>— {date}</sub>\n\n"
            f'<img src="{url}" width="680" alt="{title}" />\n\n'
            f"{expl}"
        )
    # video
    return (
        f"**{title}** <sub>— {date}</sub>\n\n"
        f"{expl}\n\n"
        f"[Watch]({url})"
    )


# ── USGS ──────────────────────────────────────────────────────────────────────

def section_usgs():
    """Top 5 earthquakes M4.5+ past 7 days. No key, no limit."""
    print("USGS...")
    data = get_json(
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        "?format=geojson&minmagnitude=4.5&orderby=magnitude&limit=5"
    )
    if not data or not data.get("features"):
        return "_No M 4.5+ earthquakes in the past 7 days._"

    rows = [
        f"<sub>Updated {utc_now()}</sub>\n",
        "| M | Location | Depth | Time (UTC) |",
        "|---|----------|-------|------------|",
    ]
    for f in data["features"]:
        p     = f["properties"]
        g     = f["geometry"]["coordinates"]
        mag   = p.get("mag", "?")
        place = (p.get("place") or "Unknown location")[:60]
        depth = f"{g[2]:.0f} km" if len(g) > 2 else "?"
        t     = datetime.fromtimestamp(
                    p["time"] / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M")
        link  = p.get("url", "#")
        rows.append(f"| **{mag}** | [{place}]({link}) | {depth} | {t} |")

    return "\n".join(rows)


# ── NOAA SWPC ─────────────────────────────────────────────────────────────────

def section_swpc():
    """Solar wind + Kp. No key, no limit."""
    print("NOAA SWPC...")
    sw = get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json")
    kp = get_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")

    lines = [f"<sub>Updated {utc_now()}</sub>\n"]

    if sw and len(sw) > 1:
        try:
            latest  = sw[-1]
            speed   = float(latest[2])
            density = float(latest[1])
            cond    = (
                "Very fast" if speed > 700 else
                "Fast"      if speed > 500 else
                "Moderate"  if speed > 350 else
                "Slow"
            )
            lines.append(
                f"**Solar wind** &nbsp; {speed:.0f} km/s — {cond}"
                f" &nbsp; Density {density:.1f} p/cm³"
            )
        except Exception:
            lines.append("**Solar wind** &nbsp; data parse error")
    else:
        lines.append("**Solar wind** &nbsp; unavailable")

    if kp and len(kp) > 1:
        try:
            kp_val  = float(kp[-1][1])
            status  = (
                "Severe storm G4–G5"   if kp_val >= 8 else
                "Strong storm G3"      if kp_val >= 6 else
                "Moderate storm G1–G2" if kp_val >= 5 else
                "Active"               if kp_val >= 4 else
                "Quiet"
            )
            aurora  = " &nbsp; Aurora possible at high latitudes." if kp_val >= 5 else ""
            lines.append(f"**Kp index** &nbsp; {kp_val:.1f} — {status}.{aurora}")
        except Exception:
            lines.append("**Kp index** &nbsp; data parse error")
    else:
        lines.append("**Kp index** &nbsp; unavailable")

    return "\n\n".join(lines)


# ── NASA NEO ─────────────────────────────────────────────────────────────────

def section_neo():
    """Near-Earth objects today. Free key."""
    print("NASA NEO...")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data  = get_json(
        f"https://api.nasa.gov/neo/rest/v1/feed"
        f"?start_date={today}&end_date={today}&api_key={NASA_KEY}"
    )
    if not data:
        return "_NASA NEO unavailable — check NASA_API_KEY secret._"

    neos = data.get("near_earth_objects", {}).get(today, [])
    if not neos:
        return f"_No close asteroid approaches on {today}._"

    def miss_dist(n):
        try:
            return float(n["close_approach_data"][0]["miss_distance"]["kilometers"])
        except Exception:
            return float("inf")

    neos = sorted(neos, key=miss_dist)[:5]

    rows = [
        f"<sub>Updated {utc_now()}</sub>\n",
        "| Object | Diameter (m) | Miss distance | Speed (km/s) | Hazardous |",
        "|--------|-------------|---------------|--------------|-----------|",
    ]
    for n in neos:
        name   = n.get("name", "?")
        hazard = "Yes" if n.get("is_potentially_hazardous_asteroid") else "No"
        dm     = n.get("estimated_diameter", {}).get("meters", {})
        dstr   = (
            f"{dm.get('estimated_diameter_min',0):.0f}–"
            f"{dm.get('estimated_diameter_max',0):.0f}"
        )
        ca   = n.get("close_approach_data", [{}])[0]
        dist = f"{float(ca.get('miss_distance',{}).get('kilometers',0)):,.0f}"
        spd  = f"{float(ca.get('relative_velocity',{}).get('kilometers_per_second',0)):.2f}"
        jpl  = n.get("nasa_jpl_url", "#")
        rows.append(f"| [{name}]({jpl}) | {dstr} | {dist} km | {spd} | {hazard} |")

    return "\n".join(rows)


# ── inject ────────────────────────────────────────────────────────────────────

def inject(text, start, end, content):
    pat = re.compile(
        rf"{re.escape(start)}.*?{re.escape(end)}",
        flags=re.DOTALL
    )
    replacement = f"{start}\n{content}\n{end}"
    result, n   = pat.subn(replacement, text)
    if n == 0:
        print(f"  WARN marker not found: {start}")
    return result


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("update_readme.py")
    print("=" * 50)

    try:
        with open("README.md", encoding="utf-8") as f:
            readme = f.read()
    except FileNotFoundError:
        print("README.md not found.")
        return

    ticker, table = section_arxiv()

    readme = inject(readme, "<!-- ARXIV_TICKER_START -->", "<!-- ARXIV_TICKER_END -->", ticker)
    readme = inject(readme, "<!-- ARXIV_LIST_START -->",   "<!-- ARXIV_LIST_END -->",   table)
    readme = inject(readme, "<!-- APOD_START -->",         "<!-- APOD_END -->",         section_apod())
    readme = inject(readme, "<!-- USGS_START -->",         "<!-- USGS_END -->",         section_usgs())
    readme = inject(readme, "<!-- SWPC_START -->",         "<!-- SWPC_END -->",         section_swpc())
    readme = inject(readme, "<!-- NEO_START -->",          "<!-- NEO_END -->",          section_neo())

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print("\nREADME.md updated.")


if __name__ == "__main__":
    main()