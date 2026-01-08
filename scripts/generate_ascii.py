import random, os, html

# 确保脚本在根目录运行时能找到路径，或者兼容脚本所在目录
BASE_DIR = os.getcwd()
ART_DIR = os.path.join(BASE_DIR, "ascii_arts")
OUTPUT_DIR = os.path.join(BASE_DIR, "dist")
FALLBACK_ART = "CODE\nLIFE" 

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

selected_art = FALLBACK_ART
if os.path.exists(ART_DIR):
    files = [f for f in os.listdir(ART_DIR) if f.endswith('.txt')]
    if files:
        try:
            with open(os.path.join(ART_DIR, random.choice(files)), "r", encoding="utf-8") as f:
                content = f.read().rstrip()
                if content.strip(): selected_art = content
        except Exception:
            pass

lines = selected_art.split("\n")

font_family = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"
font_size = 14
line_height = 1.2
# 微调了字符宽度系数
char_width_px = font_size * 0.61
line_height_px = font_size * line_height

padding_x = 40
padding_y = 40

max_chars = max(len(line) for line in lines) if lines else 0
art_width_px = max_chars * char_width_px
art_height_px = len(lines) * line_height_px

svg_width = int(art_width_px + padding_x * 2)
svg_height = int(art_height_px + padding_y * 2)

start_x = padding_x
start_y = padding_y + font_size 

tspans = ""
for i, line in enumerate(lines):
    safe_line = html.escape(line).replace(" ", "&#160;")
    dy = f'{line_height}em' if i > 0 else "0"
    tspans += f'<tspan x="{start_x}" dy="{dy}">{safe_line}</tspan>'

svg_content = f"""<svg fill="none" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect x="2" y="2" width="{svg_width-4}" height="{svg_height-4}" fill="#282a36" rx="15" ry="15" stroke="#ff79c6" stroke-width="2" stroke-opacity="0.6"/>
  <text x="{start_x}" y="{start_y}" font-family="{font_family}" font-weight="bold" font-size="{font_size}" fill="#f8f8f2" filter="url(#glow)">{tspans}</text>
</svg>"""

with open(os.path.join(OUTPUT_DIR, "ascii_art.svg"), "w", encoding="utf-8") as f:
    f.write(svg_content)
    
print("ASCII Art generated.")