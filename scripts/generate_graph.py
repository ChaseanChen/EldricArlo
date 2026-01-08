import os
import requests
from pathlib import Path

USERNAME = os.getenv("USER_NAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "activity_graph_framed.svg"

COLOR_BG = "#44475a"
COLOR_LINE = "#ff79c6"
COLOR_POINT = "#bd93f9"
COLOR_AREA = "#ff79c6"
COLOR_TEXT = "#f8f8f2"

DAYS_TO_SHOW = 30
WIDTH = 800
HEIGHT = 160
PADDING = 25
GRAPH_HEIGHT = 90

def fetch_contributions():
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.post("https://api.github.com/graphql", json={"query": query, "variables": {"user": USERNAME}}, headers=headers)
    if r.status_code != 200:
        raise Exception(f"GitHub API Error: {r.status_code}")
    
    data = r.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    
    all_days = []
    for week in weeks:
        for day in week["contributionDays"]:
            all_days.append(day)
    
    return all_days[-DAYS_TO_SHOW:]

def generate_svg(data):
    counts = [d['contributionCount'] for d in data]
    max_count = max(counts) if counts else 0
    display_max = max(max_count, 5)
    
    points = []
    count_len = len(counts)
    step_x = (WIDTH - 2 * PADDING) / (count_len - 1) if count_len > 1 else 0
    
    for i, count in enumerate(counts):
        x = PADDING + i * step_x
        y = (HEIGHT - PADDING) - (count / display_max * GRAPH_HEIGHT)
        points.append((x, y))

    path_d_start = f"M {points[0][0]},{points[0][1]} "
    path_d_lines = ""
    for p in points[1:]:
        path_d_lines += f"L {p[0]},{p[1]} "
    
    full_path = path_d_start + path_d_lines
    area_d = full_path + f"L {points[-1][0]},{HEIGHT-PADDING} L {points[0][0]},{HEIGHT-PADDING} Z"

    circles = ""
    for i, p in enumerate(points):
        if counts[i] > 0 or i == 0 or i == len(points)-1:
            circles += f'<circle cx="{p[0]}" cy="{p[1]}" r="3" fill="{COLOR_BG}" stroke="{COLOR_POINT}" stroke-width="2" />'

    svg_content = f"""
    <svg fill="none" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 12px; fill: {COLOR_TEXT}; }}
        .title {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 16px; font-weight: bold; fill: {COLOR_LINE}; }}
      </style>
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="12" ry="12" fill="{COLOR_BG}" stroke="{COLOR_LINE}" stroke-width="1" stroke-opacity="0.3" />
      <text x="{PADDING}" y="{PADDING + 5}" class="title">Contribution Activity</text>
      <text x="{WIDTH - PADDING}" y="{PADDING + 5}" class="text" text-anchor="end">Last {DAYS_TO_SHOW} Days</text>
      <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:{COLOR_AREA};stop-opacity:0.4" />
          <stop offset="100%" style="stop-color:{COLOR_AREA};stop-opacity:0.0" />
        </linearGradient>
      </defs>
      <path d="{area_d}" fill="url(#grad1)" />
      <path d="{full_path}" fill="none" stroke="{COLOR_LINE}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
      {circles}
    </svg>
    """
    return svg_content

try:
    days = fetch_contributions()
    svg = generate_svg(days)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")
except Exception:
    exit(1)