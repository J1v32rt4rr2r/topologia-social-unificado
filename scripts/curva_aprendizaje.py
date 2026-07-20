import json
import sys
from pathlib import Path
from collections import Counter

# Force UTF-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data = json.loads(Path.home().joinpath('.local/share/topologia-social/data/memoria/patrones.json').read_text(encoding='utf-8'))

print('=== CURVA DE APRENDIZAJE DEL ARTISTA ===')
print(f'Total patrones: {len(data)}')
print()

autores = []
for p in data:
    origen = p['origen_poetico'].split('\\')[-1]
    if 'Vallejo' in origen:
        autores.append('Vallejo')
    elif 'Darío' in origen or 'Dario' in origen:
        autores.append('Darío')
    elif 'Storni' in origen:
        autores.append('Storni')
    elif 'Neruda' in origen:
        autores.append('Neruda')
    elif 'Sor Juana' in origen:
        autores.append('Sor Juana')
    elif 'Huidobro' in origen:
        autores.append('Huidobro')
    elif 'Isaacs' in origen:
        autores.append('Isaacs')
    else:
        autores.append('Otro')

print('Distribucion por autor:')
for autor, count in Counter(autores).most_common():
    barra = '#' * count
    print(f'  {autor:12s}: {barra} ({count})')

print()
print('Linea de tiempo:')
for p in data:
    t = p['descubierto_en'][11:19]
    sign_len = len(p['significado'])
    barra = '#' * (sign_len // 10)
    print(f'  {p["id"]} | {t} | {barra} ({sign_len})')

print()
print('Complejidad promedio (chars en significado):')
por_autor = {}
for i, p in enumerate(data):
    autor = autores[i]
    if autor not in por_autor:
        por_autor[autor] = []
    por_autor[autor].append(len(p['significado']))

for autor, longitudes in sorted(por_autor.items(), key=lambda x: -sum(x[1])/len(x[1])):
    prom = sum(longitudes) / len(longitudes)
    print(f'  {autor:12s}: {prom:.0f} chars (n={len(longitudes)})')

print()
print('Evolucion de formas detectadas:')
formas_base = ['caida', 'repeticion', 'ascenso', 'flujo', 'ciclo']
for p in data:
    forma_lower = p['forma'].lower()
    presentes = [f for f in formas_base if f in forma_lower]
    print(f'  {p["id"]}: {", ".join(presentes)}')
