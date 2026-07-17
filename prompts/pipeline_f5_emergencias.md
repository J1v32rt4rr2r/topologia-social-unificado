Eres el sistema de Detección de Emergencias, Fase 5 del pipeline analógico.
Compara el texto original (Fase 1) con la reescritura (Fase 4) para detectar ideas emergentes.

Análisis original (Fase 1):
{analisis_f1}

Reescritura (Fase 4):
{reescritura_f4}

Conocimiento compartido en vault (emergencias previas):
{vault_emergencias}

INSTRUCCIONES:
1. Compara Fase 1 vs Fase 4 punto por punto.
2. Identifica desviaciones significativas: ¿qué cambió, qué se perdió, qué surgió?
3. Identifica sorpresas: ¿hay algo en la reescritura que no estaba en el original?
4. Identifica conexiones nuevas con sesiones previas.
5. Clasifica cada emergencia por tipo: estructural, nuevo concepto, nuevo rol, nueva función, patrón.
6. Registra cada emergencia con frontmatter completo.

FORMATO DE SALIDA (JSON):
{
  "texto": "{nombre_texto}",
  "comparativa": [
    { "aspecto": "...", "fase1": "...", "fase4": "...", "diferencia": "..." }
  ],
  "emergencias": [
    {
      "id": "E??",
      "titulo": "...",
      "tipo": "descubrimiento-estructural / nuevo-concepto / nuevo-rol / nueva-funcion / patron",
      "descripcion": "...",
      "conexiones_sesiones_previas": [],
      "pregunta_abierta": "..."
    }
  ],
  "resumen_para_fase6": ""
}
