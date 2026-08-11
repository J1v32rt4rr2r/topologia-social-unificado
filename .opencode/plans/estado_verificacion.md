# Estado Teórico — Verificación de los Puntos 1–7

Documento de seguimiento de la verificación punto por punto de la teoría
(`docs/axiomas_fractales.md` y `docs/avances_proyecto.md`) contra el código.

## 1. Unidad `u` — ✅
Núcleo en `src/topologia/math/unity.py`: identidad `e^{2πi} = 1`, operatividad
`e^{2πi/M}`, falsabilidad `e^{-2πiM}`. Tests en `tests/test_unity.py`.

## 2. 9 nodos — ✅
`NODOS_CULTURALES` define los 9 nodos (ECONOMIA…RELIGION); la observación
multi-agente los evalúa por nodo.

## 3. 3 sensores `M_m` / `M_l` / `M_s` — ✅
Tres agentes (Estadista, Filósofo, Sociólogo) valoran cada nodo en las 3
lógicas; el agregado produce `M_m`, `M_l`, `M_s` con `e^{2πi/M}`.

## 4. Plano complejo — ⚠️ parcial
- Proyección en el plano complejo: ✅ (`torus.py`, formas complejas).
- Función temporal de TRABAJO: solo discreta (hitos), no continua.

## 5. Distancias no recíprocas — 🔒 BLOQUEADO POR DATOS
Condición previa (misma que el punto 6): datos suficientes para detectar el
vector de desarrollo y su plano complejo. La suficiente hoy:

```
python scripts/verificar_suficiencia.py
```

Estado actual (2026-08-08): `BLOQUEADO` — n=24, span=33d. Lógica crítica M_l:
1.47 ciclos (<2). Hasta que el criterio esté habilitado (n≥45 y ≥2 ciclos en
las 3 lógicas), no se puede determinar las distancias; se requiere
planificación de la recolección (objetivo ~2026-09-21).

## 6. Noticia = proyección de la lógica del emisor — 🔒 BLOQUEADO (igual)
La condición es la misma que el punto 5: datos suficientes del vector de
desarrollo. La proyección ya está implementada (`nodos`), pero el "emisor como
fractal" (que cada noticia proyecte su propia lógica del emisor) requiere una
base temporal estable antes de determinar una asignación fiable.

## 7a. Grupos = subconjunto de `u` — ⚠️ parcial
- Schema `EnteFractal` con `sub_entes` / `nivel_fractal`: ✅
- El pipeline de producción no usa `sub_entes` aún.

## 7b. Fourier para el vector de desarrollo — ✅
`src/topologia/math/armonicas.py`: Lomb–Scargle sobre muestreo irregular →
`vector_desarrollo_M` (periodo/fase por lógica), `disrupcion_temporal` y
`disrupcion_M`. Integrado en el orquestador (`_aplicar_desarrollo_temporal`,
`res["vector_desarrollo"]`, `res["disrupciones"]`). Estado `preliminar` hasta n≥45.