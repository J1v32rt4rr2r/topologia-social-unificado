import urllib.request
import os

libs_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'topologia-social', 'data', 'libs')
os.makedirs(libs_dir, exist_ok=True)

urls = {
    'chart.min.js': 'https://cdn.jsdelivr.net/npm/chart.js',
    'three.min.js': 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
    'OrbitControls.js': 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js',
}

for name, url in urls.items():
    path = os.path.join(libs_dir, name)
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        print(f'Downloading {name} from {url}...')
        try:
            urllib.request.urlretrieve(url, path)
            size = os.path.getsize(path)
            print(f'  Saved: {size} bytes')
        except Exception as e:
            print(f'  ERROR: {e}')
    else:
        print(f'{name} already exists ({os.path.getsize(path)} bytes)')

print('\nDone. Files:')
for f in os.listdir(libs_dir):
    print(f'  {f} ({os.path.getsize(os.path.join(libs_dir, f))} bytes)')
