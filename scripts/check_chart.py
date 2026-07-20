from pathlib import Path
import re

html = Path(r'C:\Users\Admin\.local\share\topologia-social\data\reportes\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')

# Find all script src references
refs = re.findall(r'<script src="(.*?)"', html)
print('Script references:')
for r in refs:
    print(f'  {r}')

# Check for Chart.js
print(f'\nChart.js CDN: {"chart.js" in html.lower()}')
print(f'Has chart.min.js: {"chart.min.js" in html.lower()}')
