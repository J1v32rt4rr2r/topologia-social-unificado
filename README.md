# Topología Social

Sistema multi-agente para observación topológica de la cultura.

Modela la evolución cultural de una sociedad como un **ente fractal** `u = (identidad, estado)`: la identidad es el invariante `I(u) = e^{2πi} = 1` (Axioma U) y el estado `s(u,t)` evoluciona sobre una **tromba** — una hélice sobre `ℝ × T³`, el cubrimiento universal del toro. El toro `T³ = S¹×S¹×S¹` es la versión con memoria cerrada (tiempo periódico); la tromba abre el tiempo y la memoria se acumula (`θ(t) = ω·t`).

Tres canales (Material M, Lógico-Valórica L, Social S) forman la grilla 3×3 de acoplamientos: los **9 nodos culturales**. Su tercer orden (9×3) produce el **tecelado**: 27 vértices `p_{kj} = e^{i·θ_{kj}}` sobre el círculo unitario, con núcleo dominante y arrastre. El sistema detecta operaciones cinéticas, nodos frágiles, emergencias estructurales y calcula el **riesgo compuesto R**.

La formalización completa (axiomas U, T, C, S, F, O, D) está en [docs/axiomas_fractales.md](docs/axiomas_fractales.md).

## Arquitectura

```
src/topologia/
├── agents/          # Agentes: Estadista, Filósofo, Sociólogo, Árbitro, Artista, Redactor
├── math/            # Ente fractal: tromba ℝ×T³, tecelado, formas complejas, cinética
├── memoria/         # DecisionDB, BloquesMemoria, MemoriaRedactor (conversacional)
├── models/          # Schemas Pydantic, patrones, cliente LLM
├── pipeline/        # Pipeline analógico de 6 fases (skills/fase1-6/)
├── server/          # Servidor web FastAPI + dashboard
├── storage/         # Persistencia en archivos JSON/YAML
├── web/             # Fuentes: RSS, búsqueda, tendencias, BCN, Gutenberg, Descubridor
├── escalar/         # Escalar R: 6 índices de riesgo → compuesto → red de riesgo
├── main.py          # CLI con Typer
└── orchestrator.py  # Orquestador del ciclo diario
```

El flujo completo del ciclo diario y sus conectores están en [docs/diagrama_proyecto.md](docs/diagrama_proyecto.md).

### Modelo teórico

Un ente fractal `u` (persona = grupo = clase = sociedad, Axioma S) es una unidad con dos capas:

```
u = ( identidad, estado )
identidad:  I(u) = e^{2πi} = 1        invariante: "volver a 1"
estado:     s(u,t) = (M_m, M_l, M_s, θ_m, θ_l, θ_s)    cambia con el tiempo
```

| Axioma | Contenido |
|--------|-----------|
| **U** Unidad | `I(u) = e^{2πi} = 1`: la identidad es invariante; el cambio vive solo en el estado |
| **T** Tromba | La trayectoria `t ↦ s(u,t)` es conexa en `ℝ × T³`: la línea de mundo no se corta |
| **C** Clausura | La fase de cada canal es periódica: `θ_k(t+T) ≡ θ_k(t) mod 2π`; lo que avanza es la memoria |
| **S** Escala | El mismo objeto formal a toda escala; el esqueleto 3→9→27 es invariante |
| **F** Falsabilidad | El contenido M es no-real → `e^{-2πiM}`; la estructura emerge solo en el modo operativo |
| **O** Operatividad | `x ↦ -1/x` (involución): el ente solo computa con lo operativo (`e^{2πi/M}`) |
| **D** Densidad | El tecelado se concentra alrededor del núcleo `θ*`; la dominancia es una densidad, no una fuerza |

Cada lógica valora cada nodo con un escalar `v ∈ [0,10]`; el mapeo `θ_{kj} = 360°/v_{kj}`, `p_{kj} = e^{i·θ_{kj}}` genera los **27 vértices de contacto** (el tecelado). El núcleo es el canal dominante `k* = argmax(M_k)` con fase `θ*`; la concentración circular `R = |Σ e^{i(φ_j − θ*)} / 27|` y el **arrastre** `p* = p + λ·R·f(Δθ)·(núcleo − p)` desplazan los vértices efectivos.

### Agentes

| Agente | Dimensión | Temperatura | Función |
|--------|-----------|-------------|---------|
| **Estadista** | Material (M_m) | 0.2 | Evalúa infraestructura, recursos físicos |
| **Filósofo** | Lógica (M_l) | 0.2 | Evalúa ideologías, narrativas, principios |
| **Sociólogo** | Social (M_s) | 0.2 | Evalúa redes, relaciones, cohesión |
| **Árbitro** | Deliberación | 0.3 | Resuelve discrepancias observacionales, emite alertas |
| **Artista** | Patrones analógicos | 0.8 | Taller poético, especula sobre actualidad, propone investigaciones |
| **Redactor** | Síntesis narrativa | 0.5 | Redacta informes diarios con memoria conversacional |

### Nodos Culturales

ECONOMÍA, TRABAJO, SEXUALIDAD/REPRODUCCIÓN, POLÍTICA, LENGUAJE, ÉTICA/ESTÉTICA, TECNOLOGÍA, EDUCACIÓN, RELIGIÓN

### Escalar de Riesgo (R)

6 índices normalizados (δ_proximidad, m_contracción, θ_desviación, v_trabajo, s_activación, co_sincronía) se combinan en un compuesto ponderado `R = Σ(w_i × c_i)`:

| Nivel | Rango | Color |
|-------|-------|-------|
| Bajo | R < 0.4 | VERDE — monitoreo normal |
| Medio | 0.4 ≤ R < 0.7 | AMARILLA — reporte detallado |
| Alto | R ≥ 0.7 | ROJA — alerta en informe |

Se calibra contra 7 hitos históricos chilenos (1988–2026) y exporta redes de riesgo por fecha.

### Ente Fractal (el UNO y el tecelado social)

La identidad del ente (`e^{2πi} = 1`) y su estado evolutivo se visualizan como una **tromba** ℝ×T³ (3 hebras: M, L, S) junto con el tecelado de 27 vértices, núcleo y arrastre: `scripts/visualizar_tromba_tecelado.py`.

### Memoria

| Componente | Rol |
|-----------|-----|
| `DecisionDB` | Decisiones, patrones y estudios (`decisions.json`, `patrones.json`) |
| `BloquesMemoria` | Analogías del pipeline (visuales, cinéticas, emergentes) |
| `MemoriaRedactor` | Conversacional: buffer crudo + resumen rodante LLM + archivado mensual |

El Redactor inyecta contexto de memoria en cada informe: los días recientes íntegros (buffer acotado a ~2000 tokens), un resumen rodante generado por LLM y bloques permanentes sellados cada 30 días. El contexto total se estabiliza en ~2450 tokens (verificado con simulación de 40 días y LLM real).

### Pipeline Analógico

6 fases que transforman un texto fuente en estructuras lógicas formalizadas:

```
texto → F1(Inmersión) → F2(Pictórica) → F3(Análisis) → F4(Reescritura) → F5(Emergencias) → F6(Formalización)
```

Cada fase usa memoria de sesiones anteriores para acumular conocimiento.

## Instalación

```bash
# Clonar
git clone <repo>
cd topologia-social

# Instalar (gráficos opcionales: pip install -e ".[grafos]")
pip install -e .

# Configurar entorno
cp .env.example .env
# Editar .env con tu DEEPSEEK_API_KEY
# Recomendado: LLM_MODELO="deepseek-v4-flash" (el sistema deshabilita el
# razonamiento del modelo automáticamente para evitar respuestas vacías)
```

## Uso

```bash
# Ciclo diario completo (recolección → observación → riesgo → informe)
topologia daily

# Observar estado cultural
topologia observe

# Ver último estado
topologia state

# Aprender de un poema (pipeline analógico)
topologia learn ruta/al/poema.txt

# Pipeline analógico sobre un texto
topologia pipeline ruta/al/texto.txt

# Generar informe
topologia report

# Generar panel HTML
topologia panel

# Riesgo compuesto R
topologia riesgo

# Calibrar contra hitos históricos
topologia calibrar

# Gráficos de evolución
topologia graficos

# Analizar tendencias
topologia trends "palabra clave"

# Consultar RSS
topologia rss

# Iniciar servidor web
topologia server

# Probar conexión LLM
topologia test-llm
```

## Stack

- Python 3.11+ (verificado en 3.14)
- OpenAI SDK (compatible con DeepSeek API)
- FastAPI + Jinja2 (dashboard web)
- Pydantic (modelos)
- Typer (CLI)
- Feedparser, DuckDuckGo Search (fuentes)
- tiktoken (conteo de tokens de la memoria)
- matplotlib + numpy (gráficos, opcional `.[grafos]`)
- pytest (tests)

## Tests

```bash
pytest tests/
# Los tests de RSS (tests/test_rss.py) requieren red; omitir en offline:
pytest tests/ --ignore=tests/test_rss.py
```
