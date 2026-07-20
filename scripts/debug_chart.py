from pathlib import Path

# Check the generated HTML
html_path = Path(r'C:\Users\Admin\.local\share\topologia-social\data\reportes\panel_Chile_2026-07-18.html')
html = html_path.read_text(encoding='utf-8')

# Check for Chart.js CDN reference
if 'cdn.jsdelivr.net/npm/chart.js' in html:
    print('Chart.js CDN still present')
    # Find the exact line
    for i, line in enumerate(html.split('\n')):
        if 'chart.js' in line.lower():
            print(f'  Line {i}: {line[:200]}')
else:
    print('Chart.js CDN replaced')

# Check for inline Chart.js
if 'Chart.register' in html or 'chart.js' in html.lower():
    print('Chart.js content found inline')
