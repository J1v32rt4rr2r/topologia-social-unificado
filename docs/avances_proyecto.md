# Topología Social — Informe de Avances del Proyecto

> **Sistema de monitoreo y análisis de topología cultural chilena**
> Fecha del informe: 25 julio 2026 · Estado actual: R=0.684 (AMARILLA)

---

## 1. Resumen Ejecutivo

Topología Social es un sistema autónomo de monitoreo cultural diario que modela 9 nodos culturales (ECONOMIA, TRABAJO, SEXUALIDAD, POLITICA, LENGUAJE, ETICA_ESTETICA, TECNOLOGIA, EDUCACION, RELIGION) en 3 dimensiones (material M_m, lógica M_l, social M_s). Opera un ciclo diario completo de recolección, observación multi-agente, especulación analógica, investigación, calibración histórica y cálculo de riesgo compuesto. El sistema ha sido calibrado contra 7 hitos históricos chilenos (1988–2026) y produce informes HTML diarios con narrativa, gráficos y proyecciones.

**Estado actual del sistema cultural chileno (2026-07-25):**
- M = (5.1, 5.2, 5.2) — contracción sostenida de la suma M
- δ = 6.2° — rango S1 (0–5] normal, rozando S2
- θ = 68.6° — desviación significativa del centro histórico (57.3°)
- k = 8 — era constante, sin transición de régimen en 40 años
- Tensión = 212.5 — moderada
- R = 0.684 — AMARILLA, muy cerca del umbral ROJO (0.7)
- Hito más similar: pandemia_ola1_2020 (r=0.665)
- ECONOMIA (δ=19.1) y TECNOLOGIA (δ=14.5) son los nodos más activos

---

## 2. Arquitectura del Sistema

### 2.1 Ciclo Diario (`orchestrator.py` — `ciclo_diario()`)

| Paso | Componente | Descripción |
|------|-----------|-------------|
| 0 | Diagnóstico histórico | Genera estrategia de recolección (nodos prioritarios, brechas, umbral) |
| 1 | Recolección clásica | RSS (20), BCN (3), BCentral/BDE (28), Resumen (10), INE (17), Espectro B, YouTube (10), Trends (10) |
| 2 | Recolección estratégica | Queries dirigidas por nodo (~3 por nodo prioritario) |
| 3 | Filtro adaptativo | Scoring de relevancia + gate "Chile fuerte" (fuentes no chilenas exigen señal chilena) |
| 4 | Scraping por déficit | Búsqueda específica para nodos sub-representados |
| 5 | Descubrimiento dinámico | Búsqueda de nuevas fuentes para nodos prioritarios/déficit |
| 6 | Observación multi-agente | 9 nodos × 3 agentes × 2 rondas (hasta 54 llamadas LLM, con fallbacks) |
| 7 | Detección cinética | 6 operaciones (O3a, O4a, O5, O6, O9, O11) + O1b sistémica |
| 8 | Especulación | Artista genera patrones desde noticias + historia + memoria |
| 9 | Investigación | Web search para cada pregunta abierta; validación 3-dimensiones |
| 10 | Riesgo compuesto | 6 índices normalizados → R compuesto + red de riesgo |
| 11 | (No se ejecuta en el ciclo) | La calibración contra hitos es un paso CLI independiente: `topologia calibrar` |
| 12 | Síntesis | Redactor genera narrativa + HTML con gráficos |
| 13 | Timeline | Actualización de serie temporal + gráficos de evolución |

**Tiempo total del ciclo:** 20–30 minutos.

### 2.2 Modelo Matemático

#### Espacio Cultural 3-Toro

Cada nodo cultural se representa como un punto en un toro 3D:

```
u = (M_m / 9.9) × 2π
v = (M_l / 9.9) × 2π
x = (R + r·cos(u)) · cos(v)
y = (R + r·cos(u)) · sin(v)
z = r · sin(u)
intensidad = M_s / 9.9
```

#### Formas Complejas

Cada dimensión se proyecta en el plano complejo:

```
F = e^(2πi / M)
  → Re(F) = coherencia cultural
  → Im(F) = tensión transformativa
```

#### Delta (Dispersión Angular)

```
θ_m = 360° / M_m
θ_l = 360° / M_l
θ_s = 360° / M_s
δ = σ(θ_m, θ_l, θ_s)
```

#### Umbrales Naturales de δ

| Nivel | Rango | Interpretación |
|-------|-------|---------------|
| S0 | δ = 0 | Quietud / consenso perfecto |
| S1 | 0 < δ ≤ 5 | Coherencia estable |
| S2 | 5 < δ ≤ 8 | Tensión emergente |
| S3 | δ > 8 | Crisis / reconfiguración |

#### El UNO y el Tecelado Social (Ente Fractal)

El ente fractal `u` (persona = grupo = clase = sociedad, Axioma S) es una
unidad con identidad invariante `I(u) = e^{2πi} = 1` (Axioma U) y estado
evolutivo `s(u,t)` sobre la tromba `ℝ × T³`. Su operatividad:

```
p_{kj} = e^{i·θ_{kj}},  θ_{kj} = 360° / v_{kj}    27 vértices de contacto
k* = argmax(M_k)                                  núcleo (canal dominante)
θ* = 360° / M_{k*}                                fase dominante
R  = |Σ e^{i(φ_j − θ*)} / 27|                     concentración (Axioma D)
p* = p + λ·R·f(Δθ)·(núcleo − p)                   arrastre (vértice efectivo)
```

Ver `docs/axiomas_fractales.md` para la formalización completa (axiomas
U, T, C, S, F, O, D).

### 2.3 Agentes

| Agente | Rol | Modelo |
|--------|-----|--------|
| **Estadista** | Evalúa M_m (material) | deepseek-chat |
| **Filósofo** | Evalúa M_l (lógica) | deepseek-chat |
| **Sociólogo** | Evalúa M_s (social) | deepseek-chat |
| **Árbitro** | Deliberación heurística (sin LLM) | — |
| **Artista** | Genera especulaciones analógicas | deepseek-chat |
| **Redactor** | Sintetiza informe narrativo | deepseek-chat |

### 2.4 Operaciones Cinéticas Detectadas

| Código | Nombre | Condición |
|--------|--------|-----------|
| O3a | Vertical devocional | RELIGION.M_l - EDUCACION.M_l > 3.0 |
| O4a | Polarización | POLITICA: \|M_m - M_l\| > 3.0 |
| O5 | Entropía | 3+ nodos con M_m < 3.0 o M_s < 3.0 |
| O6 | Órbita parasítica | ECONOMIA y TRABAJO: \|M_m diff\| > 3.0 |
| O9 | Escape horizontal | TECNOLOGIA.M_m > 6 ∧ LENGUAJE.M_l > 6 ∧ SEXUALIDAD.M_m < 3 |
| O11 | Círculo expansivo | ETICA_ESTETICA.M_s > 6 ∧ EDUCACION.M_s > 6 |

---

## 3. Escalar de Riesgo Cultural (R)

### 3.1 Componentes

| Componente | Peso | Función | Rango |
|-----------|------|---------|-------|
| δ_proximidad | 0.1667 | 1 - min_distancia(hitos) / max_dist | [0, 1] |
| m_contracción | 0.1667 | 1 - (suma_M - min_M) / (baseline - min_M) | [0, 1] |
| θ_desviación | 0.1667 | \|θ - θ_base\| / rango_θ | [0, 1] |
| v_trabajo_norm | 0.1667 | min(\|v_TRABAJO\| / max_v, 1) | [0, 1] |
| s_activación | 0.1667 | min(δ_SEXUALIDAD / max_δ, 1) | [0, 1] |
| co_sincronía | 0.1667 | ρ_promedio(ECONOMIA, TRABAJO, SEXUALIDAD) | [0, 1] |

**Fórmula:** R = Σ(w_i × c_i), clamp [0, 1]

### 3.2 Umbrales de Alerta

| Nivel | Rango | Color | Acción |
|-------|-------|-------|--------|
| Bajo | R < 0.4 | VERDE | Monitoreo normal |
| Medio | 0.4 ≤ R < 0.7 | AMARILLA | Reporte detallado |
| Alto | R ≥ 0.7 | ROJA | Alerta en informe |

### 3.3 Calibración Leave-One-Out

- **MAE:** 0.2189
- **RMSE:** 0.2857
- **Método:** pesos uniformes con diagnóstico de correlación
- **Muestra:** 7 hitos históricos
- **Nota:** n=7 es pequeño; el escalar mejora con n>30

---

## 4. Hitos Históricos (Base de Calibración)

| Hito | Fecha | δ | M | θ | Tensión | Operaciones |
|------|-------|---|---|---|---------|-------------|
| plebiscito_1988 | 1988-10-01/31 | 8.4° | (5.2,6.3,6.2) | 57.3° | 270.9 | O11 |
| estallido_2019 | 2019-10-18/11-30 | 5.1° | (5.1,5.8,5.9) | 62.5° | 335.5 | O11 |
| pandemia_ola1_2020 | 2020-03-15/06-30 | 4.1° | (4.8,5.3,5.3) | 68.1° | 193.1 | — |
| pandemia_ola2_2021 | 2021-03-01/06-30 | 5.1° | (4.8,5.4,5.5) | 67.2° | 226.4 | — |
| temporal_julio_2026 | 2026-07-15/22 | 5.3° | (4.9,5.4,5.4) | 67.1° | 207.1 | — |
| plebiscito_2020 | 2020-10-01/31 | 7.5° | (4.6,5.5,5.2) | 66.0° | 312.9 | — |
| estallido_nocturno_2020 | 2020-06-01/08-31 | 5.8° | (4.9,5.5,5.1) | 65.6° | 460.6 | — |

*Valores vigentes en `config/hitos.yaml`; la calibración se ejecuta con `topologia calibrar` (CLI), no dentro del ciclo diario.*

### 4.1 Patrones Estructurales Identificados

1. **Contracción de M:** suma_M desciende de 17.7 (1988) → ~15.5 (2020s). M_m es la dimensión que más se contrae.
2. **Clusters temporales:** Grupo A "post-2020" (r > 0.65) y Grupo B "pre-2020" (r = 0.655).
3. **Cuasi-identidad:** temporal_julio_2026 y plebiscito_2020 tienen r = +0.978.
4. **Topología en Y griega (Ψ):** PCA 2D asimétrica (PC1 = 68.5%, PC2 = 17.4%).
5. **Oscilación θ:** correlación negativa con δ (r = -0.72) — los picos de crisis desplazan el ángulo cultural.
6. **k constante:** era_k = 8 en todos los hitos — 40 años sin transición de régimen.
7. **Ortogonalidad tensión-δ:** r(tensión, δ) = 0.25 — tensión y dispersión angular son variables independientes.
8. **SEXUALIDAD como amplificador:** δ salta de 0 → 25 en plebiscito_2020; nivel alto sostenido en hitos recientes.

---

## 5. Patrones Analógicos (Memoria Poética)

28 patrones estructurales descubiertos por el Artista desde poemas y noticias. Son herramientas permanentes de observación (no se refutan ni validan). Lo que se investiga son las preguntas abiertas que genera cada especulación.

**Ejemplos de patrones:**
- P-0001: Ciclo de descenso y ascenso con repetición
- P-0017: Flujo horizontal ascendente con repetición
- P-0025: Caída vertical con repetición cíclica y expansión

---

## 6. Scripts de Análisis

| Script | Propósito |
|--------|-----------|
| `scripts/serie_hito.py` | Serie temporal por hito |
| `scripts/graficos_hitos.py` | Gráficos de hitos |
| `scripts/graficos_velocidad.py` | Velocidades por nodo |
| `scripts/exportar_espacio.py` | Exporta espacio cultural |
| `scripts/embedding_espacio.py` | Embeddings del espacio |
| `scripts/calibrar_escalar.py` | Calibración del escalar R |
| `scripts/analisis_aceleracion.py` | Análisis de aceleración |
| `scripts/recoleccion_historica.py` | Recolección histórica |
| `scripts/barrido_timeline.py` | Barrido de timeline |
| `scripts/graficos_timeline.py` | Gráficos de timeline |
| `scripts/informe_topologia.py` | HTML unificado con estado+R+calibración+timeline+proyección |
| `scripts/visualizar_tromba_tecelado.py` | Tromba ℝ×T³ y tecelado de 27 vértices del ente fractal |

---

## 7. Estado del Repositorio

### 7.1 Estructura de Directorios

```
├── config/
│   ├── hitos.yaml              # 7 hitos con series y velocidades
│   ├── escalar_riesgo.json     # Escalar R: 6 componentes calibrados
│   └── periodos_historicos.yaml# 7 periodos de recolección
├── prompts/
│   ├── artista_noticias.md     # Prompt: patrones como herramientas permanentes
│   └── artista_taller.md       # Prompt: descubrimiento desde poesía
├── src/topologia/
│   ├── agents/
│   │   ├── artista.py          # especular(), taller() — patrones analógicos
│   │   ├── arbitro.py          # Resolución de conflictos entre evaluadores
│   │   ├── estadista.py        # Dimensión material (M_m)
│   │   ├── filosofo.py         # Dimensión lógica (M_l)
│   │   ├── sociologo.py        # Dimensión social (M_s)
│   │   └── redactor.py         # Síntesis narrativa del informe
│   ├── escalar/
│   │   ├── indices.py          # 6 índices de riesgo
│   │   ├── compuesto.py        # R compuesto con pesos
│   │   └── red_riesgo.py       # Exportación de red de riesgo
│   ├── math/
│   │   ├── torus.py            # Modelo 3-toro, formas complejas, δ, θ
│   │   ├── operations.py       # 6 operaciones cinéticas
│   │   ├── unity.py            # Núcleo del ente fractal (axiomas U, F, O, D)
│   │   └── coherence.py        # Evaluación de entes fractales (axioma S)
│   ├── models/
│   │   └── schemas.py          # 20 clases Pydantic (incluye EnteFractal, TipoEnte)
│   ├── memoria/
│   │   └── decisiones.py       # Almacenamiento de patrones y estudios
│   ├── storage/
│   │   └── store.py            # FileStore para estados e informes
│   └── orchestrator.py         # Ciclo diario completo
├── scripts/                    # 13 scripts de análisis
├── reportes/
│   ├── redes_riesgo/           # Redes de riesgo exportadas por fecha
│   ├── tromba_chile_3d.png     # Tromba de Chile (3 hebras M, L, S)
│   ├── tromba_relacion_3d.png  # Tromba cónica (relación de dos entes)
│   └── tecelado_chile.png      # 27 vértices + núcleo + arrastre
├── tests/
│   └── test_unity.py           # 24 tests del núcleo del ente fractal
└── docs/
    ├── avances_proyecto.md     # Este archivo
    └── axiomas_fractales.md    # Formalización del UNO y el tecelado social
```

### 7.2 Commits Recientes

```
950a729 feat: trabajo pendiente del ciclo (parser JSON LLM, biblioteca diaria, gate Chile fuerte, supervisor)
a1a9da8 chore: .gitattributes con eol=lf (normalización CRLF→LF)
de97b3a desarrollo temporal: distingue observado vs proyectado y expone confianza de la proyeccion
a946974 noticias destacadas: seleccion por score real de relevancia
af9615d retira clasificador local qwen3 (Ollama) de la destilacion 27D
ccdaaa4 destilacion 27D + fuentes estatales (bcentral/ine) + desarrollo temporal (axioma T)
```

---

## 8. Próximos Pasos

1. **Acumular observaciones diarias** para expandir el dataset a n > 30 y refinar los pesos del escalar R.
2. **Validar el escalar** contra casos de prueba pre-crisis conocidos (ej: estallido_2019, estallido_nocturno_2020).
3. **Monitorear la transición R > 0.7** — el estado actual (0.684) está a 2.3% del umbral ROJO. ECONOMIA (δ=19.1) y TECNOLOGIA (δ=14.5) son los nodos a vigilar.
4. **Refinar la detección de transiciones de era** (k actualmente constante en 8; identificar condiciones de cambio).
5. **Documentar y compartir hallazgos** de topología cultural chilena.
6. **Validar el ente fractal** (el UNO): acumular tecelados diarios para medir la evolución de R (concentración) y D (densidad del corte) a lo largo del tiempo, y contrastar la predicción de arrastre contra nodos deficientes reales.

---

*Generado automáticamente por el sistema Topología Social*
