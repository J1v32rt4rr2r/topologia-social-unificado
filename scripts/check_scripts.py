from pathlib import Path
import re

html = Path(r'C:\Users\Admin\.local\share\topologia-social\data\reportes\panel_Chile_2026-07-18.html').read_text(encoding='utf-8')

# Find all script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f'Found {len(scripts)} script tags')
for i, s in enumerate(scripts):
    content = s.strip()
    if len(content) > 100:
        print(f'  Script {i}: {len(content)} chars, starts with: {content[:80]}...')
    else:
        print(f'  Script {i}: {content[:100]}')

# Check if CDN references are gone
cdn_refs = re.findall(r'<script src="https://cdn[^"]*"', html)
print(f'\nRemaining CDN references: {len(cdn_refs)}')
for ref in cdn_refs:
    print(f'  {ref}')
