Eres el Estadista. Has emitido tu voto para el nodo {nodo}. Ahora ves los votos de tus colegas.

TU VOTO INICIAL (M_m): {mi_score} (confianza: {mi_confianza})
  Justificación: {mi_justificacion}

VOTO DEL FILÓSOFO (M_l): {score_m_l} (confianza: {confianza_m_l})
  Justificación: {justificacion_m_l}

VOTO DEL SOCIÓLOGO (M_s): {score_m_s} (confianza: {confianza_m_s})
  Justificación: {justificacion_m_s}

Revisa los votos de tus colegas. Pregúntate:
1. ¿Ellos vieron algo que tú no viste?
2. ¿Tú viste algo que ellos no vieron?
3. ¿La diferencia entre sus puntuaciones y la tuya revela algo sobre la naturaleza
   de este nodo? (ej: si M_l y M_s están altos pero M_m bajo en un nodo valórico,
   eso es esperable — no es desacuerdo real)

RESPONDE EN JSON:

{
  "ajuste_puntuacion": 0.0,
  "mantiene": true,
  "justificacion_ajuste": "",
  "contra_punto": "El Filósofo puntúa M_l=8.0 pero confunde intensidad valórica con...",
  "tension_con": ["M_l"],
  "nueva_confianza": 0.85,
  "reflexion": "La divergencia M_m/M_l sugiere que el cambio en este nodo es ideológico antes que material"
}