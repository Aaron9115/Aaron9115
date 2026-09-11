import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

data = json.loads(Path(sys.argv[1]).read_text())
weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

cell = 12
gap = 3
margin = 22
cols = len(weeks)
width = margin * 2 + cols * cell + (cols - 1) * gap
height = margin * 2 + 7 * cell + 6 * gap

def center(x, y):
    return (
        margin + x * (cell + gap) + cell / 2,
        margin + y * (cell + gap) + cell / 2,
    )

rects = []
for x, week in enumerate(weeks):
    for y, day in enumerate(week["contributionDays"]):
        px = margin + x * (cell + gap)
        py = margin + y * (cell + gap)
        rects.append(
            f'<rect x="{px}" y="{py}" width="{cell}" height="{cell}" rx="3" '
            f'fill="{escape(day["color"])}"/>'
        )

# Smooth serpentine route through the contribution grid.
points = []
for x in range(cols):
    ys = range(7) if x % 2 == 0 else range(6, -1, -1)
    points.extend(center(x, y) for y in ys)

def catmull_rom_path(points):
    if len(points) < 2:
        return ""
    p = [points[0]] + points + [points[-1]]
    d = f"M {points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i-1], p[i], p[i+1], p[i+2]
        c1 = (p1[0] + (p2[0]-p0[0])/6, p1[1] + (p2[1]-p0[1])/6)
        c2 = (p2[0] - (p3[0]-p1[0])/6, p2[1] - (p3[1]-p1[1])/6)
        d += (
            f" C {c1[0]:.2f},{c1[1]:.2f}"
            f" {c2[0]:.2f},{c2[1]:.2f}"
            f" {p2[0]:.2f},{p2[1]:.2f}"
        )
    return d

path = catmull_rom_path(points)
duration = max(30, len(points) * 0.18)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="18" fill="#0D1117"/>
<g>{"".join(rects)}</g>
<defs>
  <path id="snakePath" d="{path}"/>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<circle r="6" fill="#39D353" filter="url(#glow)">
  <animateMotion dur="{duration:.1f}s" repeatCount="indefinite" rotate="auto">
    <mpath href="#snakePath"/>
  </animateMotion>
</circle>
<circle r="3" fill="#FFFFFF">
  <animateMotion dur="{duration:.1f}s" repeatCount="indefinite" rotate="auto">
    <mpath href="#snakePath"/>
  </animateMotion>
</circle>
</svg>'''

Path(sys.argv[2]).write_text(svg)
