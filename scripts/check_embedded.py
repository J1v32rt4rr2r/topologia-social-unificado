from pathlib import Path
html = Path(r'C:\Users\Admin\.local\share\topologia-social\data\reportes\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')
print(f'File size: {len(html)} bytes')
print(f'Has CDN urls: {"cdn.jsdelivr.net" in html}')
print(f'Has inline THREE: {"THREE.Scene" in html}')
print(f'Has inline Chart: {"new Chart" in html}')
# Check if libs are embedded
print(f'chart.min.js embedded: {"Chart.register" in html[:5000]}')
print(f'three.min.js embedded: {"THREE.REVISION" in html[:5000]}')
