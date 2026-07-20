from pathlib import Path
import re

html = Path(r'C:\Users\Admin\Desktop\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')

# Find canvas elements
canvases = re.findall(r'<canvas[^>]*id="([^"]+)"', html)
print('Canvas elements:', canvases)

# Check script structure
lines = html.split('\n')
print(f'\nTotal lines: {len(lines)}')

# Check around Chart.js usage
for i, line in enumerate(lines):
    if 'new Chart' in line or 'getElementById' in line and 'chart' in line.lower():
        print(f'Line {i+1}: {line.strip()[:200]}')

# Check if Chart.js library is actually loaded properly
chart_line = None
for i, line in enumerate(lines):
    if 'Chart.js v' in line:
        chart_line = i + 1
        print(f'\nChart.js library starts at line {chart_line}')
        break

# Check if there's a syntax error in the main script
main_script_start = None
for i, line in enumerate(lines):
    if 'const historial = JSON.parse' in line:
        main_script_start = i
        break

if main_script_start:
    print(f'\nMain script starts at line {main_script_start + 1}')
    # Count braces
    brace_count = 0
    for i in range(main_script_start, len(lines)):
        line = lines[i]
        brace_count += line.count('{') - line.count('}')
    print(f'Brace balance at end: {brace_count}')
