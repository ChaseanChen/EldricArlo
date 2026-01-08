import random
import html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ART_DIR = BASE_DIR / "ascii_arts"
OUTPUT_DIR = BASE_DIR / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FALLBACK_ART = "CODE\nLIFE"
selected_art = FALLBACK_ART

if ART_DIR.exists():
    files = list(ART_DIR.glob('*.txt'))
    if files:
        try:
            chosen_file = random.choice(files)
            content = chosen_file.read_text(encoding="utf-8").rstrip()
            if content.strip():
                selected_art = content
        except Exception:
            pass

lines = selected_art.split("\n")

font_family = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"
font_size = 14
line_height = 1.2
char_width_px = font_size * 0.6
line_height_px = font_size * line_height

max_line_chars = max(len(line) for line in lines) if lines else 0
content_width = max_line_chars * char_width_px
content_height = len(lines) * line_height_px

padding_x = 60
padding_y = 50
svg_width = int(content_width + padding_x * 2)
svg_height = int(content_height + padding_y * 2)

start_y = padding_y + font_size

tspans = ""
for i, line in enumerate(lines):
    safe_line = html.escape(line).replace(" ", "&#160;")
    dy = f'{line_height}em' if i > 0 else "0"
    tspans += f'<tspan x="{padding_x}" dy="{dy}">{safe_line}</tspan>'

svg_content = f"""<svg fill="none" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect x="2" y="2" width="{svg_width-4}" height="{svg_height-4}" fill="#282a36" rx="10" ry="10" stroke="#ff79c6" stroke-width="2" stroke-opacity="0.7"/>
  <text x="0" y="{start_y}" font-family="{font_family}" font-weight="bold" font-size="{font_size}" fill="#f8f8f2" filter="url(#glow)">
    {tspans}
  </text>
</svg>"""

(OUTPUT_DIR / "ascii_art.svg").write_text(svg_content, encoding="utf-8")