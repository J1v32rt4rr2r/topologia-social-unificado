# Reporte Topologico para Agente Artista

## Resumen del Sistema

El modelo captura el **estado cultural** como un punto en un espacio de 24 dimensiones (8 nodos activos × 3 dimensiones M_m, M_l, M_s). Cada nodo representa un dominio cultural.

**Nodos activos**: ECONOMIA, TRABAJO, SEXUALIDAD, POLITICA, LENGUAJE, ETICA_ESTETICA, TECNOLOGIA, EDUCACION.

**Nodo filtrado**: RELIGION fue eliminado del dataset porque presenta delta=0 en 6/7 hitos (solo activo en plebiscito_1988 con delta=2.2). Incluirlo generaba falsos positivos en distancias y correlaciones, haciendo que hitos distintos aparecieran mas similares de lo real.

Se registraron **7 hitos historicos** (1988–2026), cada uno con:
- Un **estado global** (punto en 27D)
- Una **serie temporal interna** de 3–5 snapshots (sub-estados cada ~3 dias)
- **Velocidades vectoriales** (delta/dia, direccion, aceleracion) por nodo

## Dataset para Artista

Archivos en `reportes/` (ruta completa: `~/.local/share/topologia-social/data/reportes/`):

| Archivo | Contenido |
|---|---|
| `espacio_estados.json` | 7 estados con vectores `delta` (8D) y `mls` (24D) — RELIGION excluido |
| `trayectorias.json` | Series de snapshots con vectores completos por fecha |
| `velocidades.json` | Velocidad media, max, direccion, aceleracion por nodo/hito |
| `distancias.json` | Matriz 7×7 de distancia euclidiana y Pearson (delta y mls) |
| `resumen.json` | Tabla plana con metricas clave por hito |

## Embeddings Generados

Archivos en `reportes/`:

| Archivo | Descripcion |
|---|---|
| `embedding_pca_2d_delta.png` | PCA 2D sobre vectores δ (PC1=68.5%, PC2=17.4%) |
| `embedding_pca_3d_mls.png` | PCA 3D sobre vectores M 24D (PC1=54.3%, PC2=18.2%, PC3=13.7%) |
| `embedding_trayectorias_2d.png` | Trayectorias de snapshots en espacio PCA |
| `embedding_matriz_distancia.png` | Mapa de calor de distancias euclidianas entre hitos |
| `embedding_varianza_delta.png` | Varianza explicada por componentes (vectores δ) |
| `embedding_varianza_mls.png` | Varianza explicada por componentes (vectores M 27D) |

## Patrones Detectados (para validacion visual)

### 1. Contraccion del Espacio
La suma M ha caido de 17.7 (1988) a ~15.5 (2020s). La dimension **M_m (Material)** es la que mas se contrae (5.2 → ~4.7). En el embedding 2D, los hitos post-2020 deberian aparecer mas cerca del origen que los pre-2020.

### 2. Dos Clusters de Crisis
- **Cluster A** (post-2020): temporal_julio_2026, plebiscito_2020, estallido_nocturno_2020 (r > 0.65 entre pares)
- **Cluster B** (pre-2020): plebiscito_1988, estallido_2019 (r = 0.655)
- Pandemias (ola1, ola2) son outliers entre ambos clusters

### 3. Tension vs Delta son Ortogonales
r(tension, delta) = 0.25 — correlacion debil. En el espacio 27D, tension podria ser un eje independiente no capturado por M.

### 4. Era k = 8 constante
Los 7 hitos comparten era_k = 8. Solo varia theta_cultura (57°–68°). El regimen computacional no ha cambiado en ~40 años.

### 5. Theta Oscila con la Crisis
- θ = 57.3° (1988, estabilidad)
- θ = 68.1° (pandemia_ola1, pico)
- θ = 65.6° (estallido_nocturno, relajacion)
Las crisis abren el angulo cultural; post-crisis se contrae parcialmente.

### 6. Trayectorias Direccionales
En el grafico de trayectorias, cada hito muestra una direccion preferencial en el espacio PCA. Algunas trayectorias son paralelas entre si (misma dinamica), otras ortogonales (dinamica distinta).

## Preguntas para Artista

1. **Geometria del embedding 2D**: Los 7 puntos en PCA 2D — ¿forman un arco, un circulo, una linea recta? ¿Hay hitos que son "outliers" respecto a la forma general?

2. **Direccion de trayectorias**: Las flechas de los snapshots (t0→t4) — ¿apuntan todas en la misma direccion? ¿Hay trayectorias que se cruzan? ¿Alguna orbita es ciclica?

3. **Cuenca de tension**: Coloreando los puntos por tension (baja ~200, alta ~460), ¿ocupan regiones distintas del espacio PCA? ¿La tension alta se agrupa?

4. **Atractores**: ¿Los puntos de todos los hitos convergen a una region comun? ¿El "centro de masa" del espacio se ha desplazado entre 1988 y 2026?

5. **Simetrias**: ¿Hay nodos cuyos vectores M son imagenes especulares de otros? Por ejemplo, ECONOMIA vs TRABAJO, o SEXUALIDAD vs RELIGION.

6. **Rotacion**: ¿El angulo θ_cultura rota de manera consistente con los ejes de PCA? ¿θ corresponde a algun componente principal?

## Instrucciones

Por favor analiza los graficos en `reportes/` y responde a las preguntas arriba. Busca patrones visuales, simetrias, agrupaciones, trayectorias, y cualquier estructura geometrica que emerja. El objetivo es entender la **topologia del espacio cultural chileno** entre 1988 y 2026.

Usa los datasets JSON en `reportes/` para construir visualizaciones adicionales si es necesario.
