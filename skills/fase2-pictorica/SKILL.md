---
name: fase2-pictorica
description: Fase 2 del pipeline analógico — traducción del texto a imagen visual usando patrones visuales previos
---

# Fase 2: Traducción Pictórica

## Cuándo usarla
Después de la inmersión textual, cuando se tiene un análisis listo para convertir a imagen.

## Qué hace
1. Lee el análisis de Fase 1
2. Consulta bloque `analogia-visual` para patrones previos
3. Propone una composición visual (paleta, formas, estructura)
4. Registra nuevos patrones visuales en el bloque vía `memory_set`
5. Escribe journal entry si hay hallazgos

## Output
- Descripción pictórica estructurada
- Paleta de colores
- Composición y distribución espacial
- Metáfora visual primaria

## Instrucciones al agente
1. Lee `mmcp/analogic-config.json`
2. Lee bloque `analogia-visual`
3. Procesa el análisis de Fase 1
4. Genera composición visual
5. Actualiza bloque `analogia-visual` con nuevos hallazgos
