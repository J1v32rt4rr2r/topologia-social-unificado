---
name: fase1-inmersion
description: Fase 1 del pipeline analógico — inmersión textual, análisis del texto fuente con memoria de preferencias
---

# Fase 1: Inmersión Textual

## Cuándo usarla
Siempre que se inicia un nuevo ejercicio analógico con un texto fuente.

## Qué hace
1. Lee el texto fuente
2. Consulta el bloque `analogia-termica` para temperatura recomendada
3. Consulta `decisions.json` vía tipo `preference` para preferencias aplicables
4. Aplica LOD según `mmcp/analogic-config.json`
5. Entrega un análisis textual enriquecido con memoria previa

## Input esperado
- Texto fuente (argumento o archivo)

## Output
- Análisis textual con contexto de memoria
- Sugerencia de temperatura para la fase
- Preferencias recuperadas aplicables

## Instrucciones al agente
1. Lee `mmcp/analogic-config.json` para config
2. Usa `memory_list` para ver bloques disponibles
3. Lee bloque `analogia-termica` si existe contenido
4. Lee `decisions.json` y filtra por tipo `preference`
5. Lee el texto fuente
6. Produce análisis al nivel LOD indicado
