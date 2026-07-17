---
name: fase3-analisis
description: Fase 3 del pipeline analógico — análisis de la imagen generada, identificación de pesos visuales y relaciones
---

# Fase 3: Análisis Pictórico

## Cuándo usarla
Después de tener una descripción pictórica de Fase 2.

## Qué hace
1. Toma la salida de Fase 2
2. Consulta bloque `analogia-cinetica` para transformaciones conocidas
3. Consulta `decisions.json` por decisiones previas similares
4. Aplica temperatura fría (analítica) según `analogia-termica`
5. Identifica pesos visuales, relaciones, tensiones
6. Registra hallazgos en `decisions.json` como tipo `pattern` vía agente `nomi`

## Output
- Análisis de composición
- Pesos visuales identificados
- Relaciones entre elementos
- Decisiones de análisis registradas

## Instrucciones al agente
1. Lee `mmcp/analogic-config.json`
2. Lee bloque `analogia-cinetica`
3. Consulta `decisions.json` por patrones previos
4. Realiza análisis pictórico detallado
5. Delega a `nomi` el registro de nuevos patrones
