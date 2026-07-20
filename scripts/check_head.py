from pathlib import Path
import re

html = Path(r'C:\Users\Admin\Desktop\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')
lines = html.split('\n')

# Show lines around script tags more carefully
print("=== Script structure ===")
for i, line in enumerate(lines):
    if '<script' in line or '</script>' in line:
        print(f'Line {i+1}: {line.strip()[:120]}')

# Check if the Chart.js lib is properly closed
print("\n=== First 30 lines ===")
for i in range(min(30, len(lines))):
    print(f'{i+1}: {lines[i][:120]}')
