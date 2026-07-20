from pathlib import Path
import re

html = Path(r'C:\Users\Admin\Desktop\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')
lines = html.split('\n')

# Find where each canvas is defined vs where it's used
for canvas_id in ['orbita-canvas', 'delta-chart', 'm-chart']:
    for i, line in enumerate(lines):
        if f'id="{canvas_id}"' in line:
            print(f'Canvas {canvas_id} defined at line {i+1}')
            break

# Find where scripts are
for i, line in enumerate(lines):
    if '<script' in line and 'historial-data' not in line:
        print(f'Script tag at line {i+1}: {line.strip()[:100]}')
    if '</script>' in line:
        print(f'Close script at line {i+1}')

# Check if the closing body/html tags exist
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped in ['</body>', '</html>']:
        print(f'{stripped} at line {i+1}')
