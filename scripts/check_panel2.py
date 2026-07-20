from pathlib import Path
html = Path(r'C:\Users\Admin\.local\share\topologia-social\data\reportes\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')
idx = html.find('id="historial-data"')
end_script = html.find('</script>', idx)
print(f'script tag starts at: {idx}')
print(f'</script> found at: {end_script}')
snippet = html[end_script-20:end_script+9]
print(f'Around </script>: [{snippet}]')

# Check if there's a missing </script> tag (double check)
count = html.count('</script>')
print(f'Total </script> count: {count}')

# Check the historial-data tag specifically
tag_start = html.rfind('<script', 0, idx+10)
tag_content_end = html.find('>', idx)
print(f'Tag content end: {tag_content_end}')
print(f'Tag: {html[tag_start:tag_content_end+1]}')
