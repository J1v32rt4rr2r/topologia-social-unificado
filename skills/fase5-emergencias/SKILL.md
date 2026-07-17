---
name: fase5-emergencias
description: Fase 5 del pipeline analógico — detección de ideas emergentes, conexiones inesperadas, nuevos patrones
---

# Fase 5: Detección de Emergencias

## Cuándo usarla
Después de la reescritura, para capturar lo que surgió inesperadamente.

## Qué hace
1. Compara input (Fase 1) con output (Fase 4)
2. Identifica desviaciones, sorpresas, conexiones nuevas
3. Consulta conocimiento compartido en `.opencode/memory/knowledge/vault/`
4. Registra nuevas ideas en el vault como entries con tags `#emergente`
5. Escribe journal entry en bloque `analogia-emergente`

## Output
- Lista de ideas emergentes
- Conexiones con sesiones previas (si existen)
- Patrones nuevos descubiertos

## Instrucciones al agente
1. Lee `mmcp/analogic-config.json`
2. Compara Fase 1 con Fase 4
3. Busca en vault por tags `#emergente`
4. Crea nueva entrada en vault con frontmatter
5. Escribe journal en `analogia-emergente`
