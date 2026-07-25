# Resumen Ejecutivo — Topología Social Unificada

## Proyecto: Calibración Histórica y Escalar de Riesgo Cultural

---

## Logro

Construcción del primer **mapa del espacio cultural chileno** (1988–2026) con 7 hitos,
8 nodos activos, 24 dimensiones, y un **escalar compuesto de riesgo** (R) que se
calcula automáticamente tras cada observación y alerta sobre proximidad a
condiciones de crisis histórica.

---

## Hitos

| Fecha | Hito | δ | Tensión | Tipo |
|-------|------|---|---------|------|
| 1988 | Plebiscito retorno democracia | 8.4 | 271 | POL |
| 2019 | Estallido social | 5.1 | 336 | ESP |
| 2020 | Pandemia COVID ola 1 | 4.1 | 193 | EXT |
| 2020 | Estallido nocturno | 5.8 | **461** | ESP |
| 2020 | Plebiscito constitucional | 7.5 | 313 | POL |
| 2021 | Pandemia ola 2 | 5.1 | 226 | EXT |
| 2026 | Temporal Godzilla | 5.3 | 207 | EXT |

## Archivos Clave

- `config/hitos.yaml` — 7 hitos con estados, series, velocidades
- `config/escalar_riesgo.json` — Escalar calibrado (MAE=0.22)
- `reportes/informe_final_calibracion.md` — Informe completo
- `src/topologia/escalar/` — Módulo del escalar (6 componentes)
- `scripts/` — 8 scripts de generación y análisis

## Estado Actual

- [x] 7 hitos recolectados y procesados
- [x] Filtrado de nodo RELIGION (falso positivo)
- [x] 6 series temporales con velocidades
- [x] Embeddings PCA 2D/3D del espacio cultural
- [x] Escalar R integrado en Orchestrator (post-observe)
- [x] Archivos de red exportados por fecha
- [x] Calibración leave-one-out completada
- [x] Comando `opencode riesgo` funcional

## Próximo

Acumular observaciones diarias para refinar pesos con regresión no negativa (n>30).
