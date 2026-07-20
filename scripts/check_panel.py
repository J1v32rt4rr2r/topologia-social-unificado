import json
from pathlib import Path

html = Path(r'C:\Users\Admin\.local\share\topologia-social\data\reportes\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')

# Extract historial JSON
marker = 'id="historial-data" type="application/json">'
start = html.find(marker) + len(marker)
end = html.find('</script>', start)
historial_json = html[start:end]

try:
    historial = json.loads(historial_json)
    print(f'Historial: {len(historial)} observaciones')
    for h in historial:
        print(f'  {h["fecha"]}: M=({h["M_m"]}, {h["M_l"]}, {h["M_s"]}), delta={h["delta"]}')
except Exception as e:
    print(f'Error parsing JSON: {e}')
    print(f'JSON length: {len(historial_json)}')
    print(f'First 500 chars: {historial_json[:500]}')
