---
name: fase4-reescritura
description: Fase 4 del pipeline analógico — reescritura del texto original enriquecido por el análisis pictórico
---

# Fase 4: Reescritura Enriquecida

## Cuándo usarla
Después del análisis pictórico, cuando se tienen ambos: texto original y su representación visual analizada.

## Qué hace
1. Toma texto original (Fase 1) + descripción pictórica (Fase 2) + análisis (Fase 3)
2. Consulta bloque `analogia-emergente` por patrones de integración previos
3. Re-escribe el texto incorporando la dimensión visual
4. Registra la integración en el bloque `analogia-emergente`

## Output
- Texto reescrito enriquecido con capa visual
- Notas de integración texto+imagen

## Instrucciones al agente
1. Lee `mmcp/analogic-config.json`
2. Lee bloque `analogia-emergente`
3. Integra texto + imagen en reescritura
4. Actualiza bloque con patrón de integración usado
