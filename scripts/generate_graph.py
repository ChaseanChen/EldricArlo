import os
import requests
import math

# 从环境变量获取 Token
USERNAME = os.getenv("USER_NAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    print("Error: Environment variables USER_NAME or GITHUB_TOKEN missing.")
    exit(1)

OUTPUT_PATH = "dist/activity_graph_framed.svg"
if not os.path.exists("dist"):
    os.makedirs("dist")

COLOR_BG = "#44475a"
COLOR_LINE = "#ff79c6"
COLOR_POINT = "#bd93f9"
COLOR_AREA = "#ff79c6"
COLOR_TEXT = "#f8f8f2"

DAYS_TO_SHOW = 31
WIDTH = 800
HEIGHT = 150
PADDING = 20
GRAPH_HEIGHT = 80

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
    max_count = max(counts) if counts else 1
    if max_count == 0: max_count = 1
    
    points = []
    step_x = (WIDTH - 2 * PADDING) / (len(counts) - 1) if len(counts) > 1 else 0
    
    for i, count in enumerate(counts):
        x = PADDING + i * step_x
        y = (HEIGHT - PADDING) - (count / max_count * GRAPH_HEIGHT)
        points.append((x, y))

    path_d = f"M {points[0][0]},{points[0][1]} "
    for p in points[1:]:
        path_d += f"L {p[0]},{p[1]} "
    
    area_d = path_d + f"L {points[-1][0]},{HEIGHT-PADDING} L {points[0][0]},{HEIGHT-PADDING} Z"

    circles = ""
    for p in points:
        circles += f'<circle cx="{p[0]}" cy="{p[1]}" r="3" fill="{COLOR_BG}" stroke="{COLOR_POINT}" stroke-width="2" />'

    svg_content = f"""
    <svg fill="none" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; fill: {COLOR_TEXT}; }}
      </style>
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="10" ry="10" fill="{COLOR_BG}" />
      <text x="{PADDING}" y="{PADDING + 10}" class="text" font-weight="bold" font-size="14">Activity (Last 31 Days)</text>
      <path d="{area_d}" fill="{COLOR_AREA}" fill-opacity="0.2" />
      <path d="{path_d}" fill="none" stroke="{COLOR_LINE}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
      {circles}
    </svg>
    """
    return svg_content

try:
    days = fetch_contributions()
    svg = generate_svg(days)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print("Graph generated.")
except Exception as e:
    print(f"Error: {e}")
    exit(1)