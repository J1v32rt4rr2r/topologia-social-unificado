from pathlib import Path

# Extract the chart.min.js from the panel
html_path = Path(r'C:\Users\Admin\Desktop\panel_Chile_2026-07-18.html')
html = html_path.read_text(encoding='utf-8')

# Create a simple test HTML
test_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Test Chart</title>
<style>
body { background: #1a1a2e; color: white; padding: 20px; }
canvas { background: #16213e; }
</style>
</head>
<body>
<h2>Test Chart</h2>
<div style="height:300px;"><canvas id="test-chart"></canvas></div>

<script>
"""

# Find Chart.js code
import re
# Find the first <script> tag content (Chart.js)
match = re.search(r'<script>\s*/\*!(.*?)</script>', html, re.DOTALL)
if match:
    chart_code = match.group(1)[:100]
    print(f"Chart.js starts with: {chart_code}")
    
# Find everything between first <script> and second <script>
first_script = html.find('<script>')
second_script = html.find('<script>', first_script + 8)
third_script = html.find('<script>', second_script + 8)

chart_lib = html[first_script+8:second_script]
print(f"Chart.js lib length: {len(chart_lib)}")

test_html += chart_lib + """

new Chart(document.getElementById('test-chart'), {
  type: 'line',
  data: { 
    labels: ['A', 'B', 'C', 'D', 'E'], 
    datasets: [{ label: 'Test', data: [1, 3, 2, 4, 3], borderColor: '#e94560', tension: 0.3 }] 
  },
  options: { responsive: true, maintainAspectRatio: false }
});
</script>
</body>
</html>"""

out_path = Path(r'C:\Users\Admin\Desktop\test_chart.html')
out_path.write_text(test_html, encoding='utf-8')
print(f"Test file written: {out_path}")
print(f"Test file size: {out_path.stat().st_size} bytes")
