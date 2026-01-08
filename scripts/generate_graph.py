import os
import requests
import math
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path

# --- Configuration & Aesthetics ---
USERNAME = os.getenv("USER_NAME")
TOKEN = os.getenv("GITHUB_TOKEN")

if not USERNAME or not TOKEN:
    print("Error: Environment variables USER_NAME or GITHUB_TOKEN are missing.")
    exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "activity_graph_framed.svg"

# Dracula Theme Palette (Cyberpunk & Vampire aesthetics)
COLOR_BG = "#44475a"
COLOR_LINE = "#ff79c6"       # Pink for the main line
COLOR_POINT = "#bd93f9"      # Purple for dots
COLOR_POINT_HOVER = "#50fa7b" # Green for hover interaction
COLOR_AREA = "#ff79c6"       # Gradient color
COLOR_TEXT = "#f8f8f2"       # White-ish text
COLOR_AXIS = "#6272a4"       # Blue-ish gray for axis text

DAYS_TO_SHOW = 30
WIDTH = 800
HEIGHT = 200  # Increased height for labels
PADDING_TOP = 40
PADDING_BOTTOM = 40 # Space for dates
PADDING_X = 40
GRAPH_HEIGHT = HEIGHT - PADDING_TOP - PADDING_BOTTOM

def get_session():
    """Create a robust session with retries."""
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
            raise Exception(f"GraphQL Error: {data['errors']}")
            
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        all_days = [day for week in weeks for day in week["contributionDays"]]
        return all_days[-DAYS_TO_SHOW:]
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        raise

def get_smooth_path(points):
    """
    Generates a smooth cubic bezier path string from a list of points.
    This creates that 'premium' look instead of jagged lines.
    """
    if not points:
        return ""
    
    path = f"M {points[0][0]},{points[0][1]}"
    
    # Simple smoothing strategy: Control points based on tangent logic could be complex.
    # We will use a simplified Catmull-Rom to Cubic Bezier conversion logic logic 
    # or a simple quadratic curve for simplicity in a script.
    # Let's use a simplified approach: connect midpoints.
    
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i+1]
        
        # Calculate control points (basic smoothing)
        cp1_x = p0[0] + (p1[0] - p0[0]) / 2
        cp1_y = p0[1]
        
        cp2_x = p0[0] + (p1[0] - p0[0]) / 2
        cp2_y = p1[1]
        
        path += f" C {cp1_x},{cp1_y} {cp2_x},{cp2_y} {p1[0]},{p1[1]}"
        
    return path

def generate_svg(data):
    counts = [d['contributionCount'] for d in data]
    dates = [d['date'] for d in data]
    
    max_count = max(counts) if counts else 0
    display_max = max(max_count, 5) # Ensure graph isn't flat if max is small
    
    points = []
    count_len = len(counts)
    step_x = (WIDTH - 2 * PADDING_X) / (count_len - 1) if count_len > 1 else 0
    
    # Calculate Coordinates
    for i, count in enumerate(counts):
        x = PADDING_X + i * step_x
        # Invert Y because SVG y=0 is top
        y = (HEIGHT - PADDING_BOTTOM) - (count / display_max * GRAPH_HEIGHT)
        points.append((x, y))

    if not points:
        return ""

    # Generate Paths
    path_d_smooth = get_smooth_path(points)
    
    # Close the path for the gradient area fill
    area_d = f"{path_d_smooth} L {points[-1][0]},{HEIGHT-PADDING_BOTTOM} L {points[0][0]},{HEIGHT-PADDING_BOTTOM} Z"

    # Generate Date Labels (X-Axis) - Show every 5th day roughly
    date_labels = ""
    for i in range(0, len(points), 5):
        # Format date usually "YYYY-MM-DD" -> "MM-DD"
        dt_obj = datetime.strptime(dates[i], "%Y-%m-%d")
        fmt_date = dt_obj.strftime("%b %d")
        
        date_labels += f'<text x="{points[i][0]}" y="{HEIGHT - 15}" class="axis-text" text-anchor="middle">{fmt_date}</text>'

    # Generate Interactivity Dots (Tooltips & Hover)
    circles = ""
    for i, p in enumerate(points):
        count = counts[i]
        date_str = dates[i]
        # Native tooltip via <title>
        tooltip = f"{date_str}: {count} contributions"
        
        # We draw an invisible larger circle for easier hovering, and a visible smaller one
        circles += f"""
        <g class="point-group">
            <circle cx="{p[0]:.2f}" cy="{p[1]:.2f}" r="4" class="visible-point" />
            <circle cx="{p[0]:.2f}" cy="{p[1]:.2f}" r="15" fill="transparent" class="hit-area">
                <title>{tooltip}</title>
            </circle>
        </g>
        """

    # CSS Animations & Styles
    # stroke-dasharray is set to 3000 (enough to cover the path width)
    svg_content = f"""
    <svg fill="none" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .text {{ font-family: 'Segoe UI', Ubuntu, Sans-Serif; font-size: 12px; fill: {COLOR_TEXT}; }}
        .title {{ font-family: 'Segoe UI', Ubuntu, Sans-Serif; font-size: 18px; font-weight: bold; fill: {COLOR_LINE}; }}
        .axis-text {{ font-family: 'Segoe UI', Ubuntu, Sans-Serif; font-size: 10px; fill: {COLOR_AXIS}; }}
        
        /* Animation Definitions */
        @keyframes drawLine {{
            from {{ stroke-dashoffset: 3000; }}
            to {{ stroke-dashoffset: 0; }}
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        @keyframes popIn {{
            from {{ r: 0; }}
            to {{ r: 4; }}
        }}

        /* Apply Animations */
        .line-path {{
            stroke-dasharray: 3000;
            stroke-dashoffset: 3000;
            animation: drawLine 2s ease-out forwards;
        }}
        .area-fill {{
            opacity: 0;
            animation: fadeIn 2s ease-out 0.5s forwards; /* Delay fill slightly */
        }}
        .visible-point {{
            fill: {COLOR_BG};
            stroke: {COLOR_POINT};
            stroke-width: 2;
            transition: all 0.2s ease;
            animation: popIn 0.5s ease-out forwards;
        }}
        
        /* Hover Interaction */
        .point-group:hover .visible-point {{
            fill: {COLOR_POINT_HOVER};
            stroke: {COLOR_TEXT};
            r: 6;
            stroke-width: 3;
            cursor: pointer;
        }}
      </style>

      <!-- Background Card -->
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="15" ry="15" fill="{COLOR_BG}" stroke="{COLOR_LINE}" stroke-width="1" stroke-opacity="0.2" />
      
      <!-- Titles -->
      <text x="{PADDING_X}" y="{PADDING_TOP - 15}" class="title">Contribution Activity</text>
      <text x="{WIDTH - PADDING_X}" y="{PADDING_TOP - 15}" class="text" text-anchor="end">Last {DAYS_TO_SHOW} Days</text>
      
      <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:{COLOR_AREA};stop-opacity:0.5" />
          <stop offset="100%" style="stop-color:{COLOR_AREA};stop-opacity:0.0" />
        </linearGradient>
      </defs>

      <!-- Graph Area -->
      <path d="{area_d}" fill="url(#grad1)" class="area-fill" />
      <path d="{path_d_smooth}" fill="none" stroke="{COLOR_LINE}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="line-path" />
      
      <!-- Axis Labels -->
      {date_labels}

      <!-- Interactive Points -->
      {circles}
    </svg>
    """
    return svg_content

try:
    days = fetch_contributions()
    svg = generate_svg(days)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Successfully generated animated graph at {OUTPUT_PATH}")
except Exception as e:
    print(f"Error generating graph: {e}")
    exit(1)