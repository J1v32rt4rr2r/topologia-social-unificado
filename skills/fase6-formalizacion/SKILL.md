---
name: fase6-formalizacion
description: Fase 6 del pipeline analógico — formalización de lo aprendido en estructuras lógicas reutilizables
---

# Fase 6: Formalización

## Cuándo usarla
Como fase final del pipeline, cuando todas las anteriores están completas.

## Qué hace
1. Recopila outputs de Fases 1-5
2. Consulta `decisions.json` para validar contra decisiones previas
3. Extrae estructuras lógicas: reglas, axiomas, patrones formales
4. Registra como decisiones tipo `lesson` vía `nomi`
5. Actualiza los 4 bloques de memoria con resumen de lo aprendido
6. Escribe entrada en vault con tags `#formalizacion`

## Output
- Estructuras lógicas formalizadas
- Lecciones aprendidas
- Bloques de memoria actualizados
- Entrada en hive mind

## Instrucciones al agente
1. Recopila outputs de fases 1-5
2. Lee `decisions.json` para validación
3. Delega a `nomi` el registro de lecciones
4. Actualiza los 4 bloques vía `memory_set`
5. Crea entrada en vault con tags `#formalizacion`
