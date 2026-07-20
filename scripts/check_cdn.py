from pathlib import Path
html = Path(r'C:\Users\Admin\Desktop\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')
import re
scripts = re.findall(r'<script src="(.*?)"', html)
for s in scripts:
    print(s)
print("---")
print(f"Chart.js canvas count: {html.count('delta-chart')}")
print(f"Three.js canvas count: {html.count('orbita-canvas')}")
print(f"new Chart count: {html.count('new Chart')}")
print(f"THREE count: {html.count('THREE.')}")
