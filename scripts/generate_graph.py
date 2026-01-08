import os
import requests
import uuid
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from datetime import datetime

# --- Configuration ---
USERNAME = os.getenv("USER_NAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    print("Error: Environment variables USER_NAME or GITHUB_TOKEN are missing.")
    exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "activity_graph_framed.svg"

# Dracula Theme
COLOR_BG = "#44475a"
COLOR_LINE = "#ff79c6"
COLOR_POINT = "#bd93f9"
COLOR_AREA = "#ff79c6"
COLOR_TEXT = "#f8f8f2"
COLOR_AXIS = "#6272a4"

DAYS_TO_SHOW = 30
WIDTH = 800
HEIGHT = 200
PADDING_TOP = 40
PADDING_BOTTOM = 40
PADDING_X = 40
GRAPH_HEIGHT = HEIGHT - PADDING_TOP - PADDING_BOTTOM

# 生成唯一ID
UNIQUE_ID = str(uuid.uuid4())[:8]

def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def fetch_contributions():
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {TOKEN}"}
    session = get_session()
    
    try:
        r = session.post("https://api.github.com/graphql", json={"query": query, "variables": {"user": USERNAME}}, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise Exception(data['errors'])
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        all_days = [day for week in weeks for day in week["contributionDays"]]
        return all_days[-DAYS_TO_SHOW:]
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        raise

def get_smooth_path(points):
    if not points: return ""
    path = f"M {points[0][0]},{points[0][1]}"
    for i in range(len(points) - 1):
        p0, p1 = points[i], points[i+1]
        mid_x = (p0[0] + p1[0]) / 2
        path += f" C {mid_x},{p0[1]} {mid_x},{p1[1]} {p1[0]},{p1[1]}"
    return path

def generate_svg(data):
    counts = [d['contributionCount'] for d in data]
    dates = [d['date'] for d in data]
    
    max_count = max(counts) if counts else 0
    display_max = max(max_count, 5)
    
    points = []
    count_len = len(counts)
    step_x = (WIDTH - 2 * PADDING_X) / (count_len - 1) if count_len > 1 else 0
    
    for i, count in enumerate(counts):
        x = PADDING_X + i * step_x
        y = (HEIGHT - PADDING_BOTTOM) - (count / display_max * GRAPH_HEIGHT)
        points.append((x, y))

    if not points: return ""

    path_d_smooth = get_smooth_path(points)
    area_d = f"{path_d_smooth} L {points[-1][0]},{HEIGHT-PADDING_BOTTOM} L {points[0][0]},{HEIGHT-PADDING_BOTTOM} Z"

    # 日期标签
    date_labels = ""
    for i in range(0, len(points), 5):
        dt_obj = datetime.strptime(dates[i], "%Y-%m-%d")
        fmt_date = dt_obj.strftime("%m-%d")
        date_labels += f'<text x="{points[i][0]}" y="{HEIGHT - 15}" class="axis-text" text-anchor="middle">{fmt_date}</text>'

    # 数据点
    circles = ""
    for i, p in enumerate(points):
        if counts[i] > 0 or i == len(points) - 1:
            circles += f'<circle cx="{p[0]:.2f}" cy="{p[1]:.2f}" r="3" class="visible-point" />'

    # --- 核心修改：循环动画逻辑 ---
    # 总时长 10秒
    # 0% - 20% (0-2秒): 线条绘制 + 渐变淡入
    # 20% - 90% (2-9秒): 保持静止展示
    # 90% - 100% (9-10秒): 快速淡出，重置
    svg_content = f"""
    <svg fill="none" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 12px; fill: {COLOR_TEXT}; }}
        .title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 18px; font-weight: bold; fill: {COLOR_LINE}; }}
        .axis-text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10px; fill: {COLOR_AXIS}; }}
        
        /* 1. 线条动画：画出 -> 停留 -> 消失 -> 循环 */
        @keyframes drawCycle_{UNIQUE_ID} {{
            0% {{ stroke-dashoffset: 3000; opacity: 1; }}
            20% {{ stroke-dashoffset: 0; opacity: 1; }} 
            90% {{ stroke-dashoffset: 0; opacity: 1; }} 
            95% {{ stroke-dashoffset: 0; opacity: 0; }}
            100% {{ stroke-dashoffset: 3000; opacity: 0; }}
        }}

        /* 2. 面积填充动画：淡入 -> 停留 -> 消失 -> 循环 */
        @keyframes fillCycle_{UNIQUE_ID} {{
            0% {{ opacity: 0; }}
            20% {{ opacity: 0; }}
            30% {{ opacity: 1; }}
            90% {{ opacity: 1; }}
            100% {{ opacity: 0; }}
        }}

        /* 3. 点动画：弹处 -> 停留 -> 消失 -> 循环 */
        @keyframes pointCycle_{UNIQUE_ID} {{
            0% {{ r: 0; opacity: 0; }}
            20% {{ r: 0; opacity: 0; }}
            25% {{ r: 4; opacity: 1; }}
            90% {{ r: 4; opacity: 1; }}
            100% {{ r: 0; opacity: 0; }}
        }}

        .line-path {{
            stroke-dasharray: 3000;
            stroke-dashoffset: 3000;
            animation: drawCycle_{UNIQUE_ID} 10s ease-in-out infinite;
        }}
        .area-fill {{
            opacity: 0;
            animation: fillCycle_{UNIQUE_ID} 10s ease-in-out infinite;
        }}
        .visible-point {{
            fill: {COLOR_BG};
            stroke: {COLOR_POINT};
            stroke-width: 2;
            opacity: 0;
            animation: pointCycle_{UNIQUE_ID} 10s ease-in-out infinite;
        }}
      </style>

      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="10" ry="10" fill="{COLOR_BG}" stroke="{COLOR_LINE}" stroke-width="1" stroke-opacity="0.3" />
      
      <text x="{PADDING_X}" y="{PADDING_TOP - 15}" class="title">Contribution Activity</text>
      <text x="{WIDTH - PADDING_X}" y="{PADDING_TOP - 15}" class="text" text-anchor="end">Last {DAYS_TO_SHOW} Days</text>
      
      <defs>
        <linearGradient id="grad_{UNIQUE_ID}" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:{COLOR_AREA};stop-opacity:0.5" />
          <stop offset="100%" style="stop-color:{COLOR_AREA};stop-opacity:0.0" />
        </linearGradient>
      </defs>

      <path d="{area_d}" fill="url(#grad_{UNIQUE_ID})" class="area-fill" />
      <path d="{path_d_smooth}" fill="none" stroke="{COLOR_LINE}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="line-path" />
      
      {date_labels}
      {circles}
    </svg>
    """
    return svg_content

try:
    days = fetch_contributions()
    svg = generate_svg(days)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Generated looping animated graph at {OUTPUT_PATH}")
except Exception as e:
    exit(1)