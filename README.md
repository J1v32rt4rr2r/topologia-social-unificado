# Topología Social

Sistema multi-agente para observación topológica de la cultura.

Modela la evolución cultural de una sociedad mediante 9 nodos en un toro 3D, cada uno evaluado en tres dimensiones (Material, Lógica, Social). Detecta operaciones cinéticas, nodos frágiles y emergencias estructurales.

## Arquitectura

```
src/topologia/
├── agents/          # Agentes: Artista, Estadista, Filósofo, Sociólogo, Redactor
├── math/            # Modelo torsional (torus 3D, operaciones cinéticas)
├── memoria/         # Sistema de decisiones y bloques de memoria
├── models/          # Schemas Pydantic, patrones, cliente LLM
├── pipeline/        # Pipeline analógico de 6 fases
├── server/          # Servidor web FastAPI + dashboard
├── storage/         # Persistencia en archivos JSON/YAML
├── web/             # Fuentes: RSS, búsqueda, tendencias, BCN, Gutenberg
├── reportes/        # Generación de informes y paneles HTML
├── main.py          # CLI con Typer
└── orchestrator.py  # Orquestador del ciclo diario
```

### Agentes

| Agente | Dimensión | Temperatura | Función |
|--------|-----------|-------------|---------|
| **Estadista** | Material (M_m) | 0.2 | Evalúa infraestructura, recursos físicos |
| **Filósofo** | Lógica (M_l) | 0.2 | Evalúa ideologías, narrativas, principios |
| **Sociólogo** | Social (M_s) | 0.2 | Evalúa redes, relaciones, cohesión |
| **Artista** | Patrones analógicos | 0.8 | Descubre patrones en poesía, especula sobre actualidad |
| **Redactor** | Síntesis narrativa | 0.5 | Redacta informes diarios |

### Nodos Culturales

ECONOMÍA, TRABAJO, CONTINUIDAD, POLÍTICA, LENGUAJE, ÉTICA/ESTÉTICA, TECNOLOGÍA, EDUCACIÓN, RELIGIÓN

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

# Instalar
pip install -e .

# Configurar entorno
cp .env.example .env
# Editar .env con tu DEEPSEEK_API_KEY
```

## Uso

```bash
# Ciclo diario completo
topologia daily

# Observar estado cultural
topologia observe

# Ver último estado
topologia state

# Pipeline analógico sobre un poema
topologia pipeline ruta/al/poema.txt

# Iniciar servidor web
topologia server

# Generar informe
topologia report

# Generar panel HTML
topologia panel

# Analizar tendencias
topologia trends "palabra clave"

# Probar conexión LLM
topologia test-llm
```

## Stack

- Python 3.11+
- OpenAI SDK (compatible con DeepSeek API)
- FastAPI + Jinja2 (dashboard web)
- Pydantic (modelos)
- Typer (CLI)
- Feedparser, DuckDuckGo Search (fuentes)
- pytest (tests)

## Tests

```bash
pytest tests/
```
