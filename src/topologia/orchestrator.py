from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path

from topologia.agents.arbitro import Arbitro
from topologia.agents.artista import Artista
from topologia.agents.estadista import Estadista
from topologia.agents.filosofo import Filosofo
from topologia.agents.redactor import Redactor
from topologia.agents.sociologo import Sociologo
from topologia.logger import logger
from topologia.math.operations import detectar_operaciones
from topologia.math.torus import (
    calcular_angulos,
    calcular_delta,
    coherencia_formas,
    coherencia_global,
    detectar_vuelco,
    diferencia_angular,
    forma_cultural_compleja,
    forma_transversal,
    tension_sistema,
    theta_cultura,
    theta_nodo,
)
from topologia.memoria.decisiones import DecisionDB
from topologia.models.schemas import (
    EstadoCultural,
    Estudio,
    EvaluacionNodo,
    InformeDiario,
    TendenciaDim,
)
from topologia.storage.store import FileStore
from topologia.web.brechas import (
    clasificar_items_por_nodo_semantico,
    detectar_brechas,
    resumen_brechas,
    terminos_para_nodo,
)
from topologia.web.rss import obtener_items as obtener_items_rss
from topologia.web.search import buscar_para_estudio
from topologia.web.bcn import obtener_items as obtener_items_bcn
from topologia.web.resumen import obtener_items as obtener_items_resumen
from topologia.web.youtube import buscar as buscar_youtube
from topologia.web.espectro_b import obtener_items as obtener_items_espectro_b
from topologia.web.tendencias import obtener_tendencias
from topologia.web.analisis_historico import diagnosticar
from topologia.web.relevancia import (
    generar_queries,
    puntuar_relevancia,
    recolectar_por_queries,
)


NODOS_CULTURALES = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]


class Orchestrator:
    def __init__(self):
        self.artista = Artista()
        self.estadista = Estadista()
        self.filosofo = Filosofo()
        self.sociologo = Sociologo()
        self.arbitro = Arbitro()
        self.redactor = Redactor()
        self.memoria = DecisionDB()
        self.store = FileStore()

    def observar(self, sociedad: str = "Chile", items: list | None = None) -> EstadoCultural:
        logger.info(f"Iniciando observación: {sociedad}")
        if items is None:
            items = obtener_items_rss(limite=30)

        evaluaciones: list[EvaluacionNodo] = []
        ultimo_estado = self.store.cargar_estado(sociedad)

        for nodo_id in NODOS_CULTURALES:
            score_anterior_m = 5.0
            score_anterior_l = 5.0
            score_anterior_s = 5.0
            just_anterior_m = ""
            just_anterior_l = ""
            just_anterior_s = ""

            if ultimo_estado:
                for n in ultimo_estado.nodos:
                    if n.nodo_id == nodo_id:
                        score_anterior_m = n.dimension_m
                        score_anterior_l = n.dimension_l
                        score_anterior_s = n.dimension_s
                        just_anterior_m = n.justificacion_m
                        just_anterior_l = n.justificacion_l
                        just_anterior_s = n.justificacion_s

            terminos = terminos_para_nodo(nodo_id)
            import unicodedata
            def _norm(s: str) -> str:
                return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
            items_filtrados = [
                it for it in items
                if getattr(it, "nodo_sugerido", None) == nodo_id
                or any(_norm(t) in _norm(it.titulo + " " + (it.contenido or ""))
                       for t in terminos)
            ]
            if not items_filtrados:
                items_filtrados = items[:5]
            logger.info(f"[{nodo_id}] items filtrados: {len(items_filtrados)}")

            # RONDA 1: cada evaluador ve las puntuaciones de ayer de los otros
            voto_m = self.estadista.evaluar_nodo(
                nodo_id, items_filtrados,
                score_anterior_m, just_anterior_m,
                puntuacion_m_l=score_anterior_l,
                justificacion_m_l=just_anterior_l,
                puntuacion_m_s=score_anterior_s,
                justificacion_m_s=just_anterior_s,
            )
            voto_l = self.filosofo.evaluar_nodo(
                nodo_id, items_filtrados,
                score_anterior_l, just_anterior_l,
                puntuacion_m_m=score_anterior_m,
                justificacion_m_m=just_anterior_m,
                puntuacion_m_s=score_anterior_s,
                justificacion_m_s=just_anterior_s,
            )
            voto_s = self.sociologo.evaluar_nodo(
                nodo_id, items_filtrados,
                score_anterior_s, just_anterior_s,
                puntuacion_m_m=score_anterior_m,
                justificacion_m_m=just_anterior_m,
                puntuacion_m_l=score_anterior_l,
                justificacion_m_l=just_anterior_l,
            )

            # RONDA 2: deliberación con las puntuaciones frescas de hoy
            deliberacion_m = self.estadista.deliberar(nodo_id, voto_m,
                {"M_l": voto_l, "M_s": voto_s})
            deliberacion_l = self.filosofo.deliberar(nodo_id, voto_l,
                {"M_m": voto_m, "M_s": voto_s})
            deliberacion_s = self.sociologo.deliberar(nodo_id, voto_s,
                {"M_m": voto_m, "M_l": voto_l})

            # Aplicar ajustes de la deliberación
            score_m = max(0.1, min(9.9, voto_m.score + deliberacion_m.get("ajuste", 0.0)))
            score_l = max(0.1, min(9.9, voto_l.score + deliberacion_l.get("ajuste", 0.0)))
            score_s = max(0.1, min(9.9, voto_s.score + deliberacion_s.get("ajuste", 0.0)))

            voto_m.score = round(score_m, 1)
            voto_m.confianza = deliberacion_m.get("nueva_confianza", voto_m.confianza)
            voto_m.contra_punto = deliberacion_m.get("contra_punto", voto_m.contra_punto)
            voto_m.tension_con = deliberacion_m.get("tension_con", voto_m.tension_con)

            voto_l.score = round(score_l, 1)
            voto_l.confianza = deliberacion_l.get("nueva_confianza", voto_l.confianza)
            voto_l.contra_punto = deliberacion_l.get("contra_punto", voto_l.contra_punto)
            voto_l.tension_con = deliberacion_l.get("tension_con", voto_l.tension_con)

            voto_s.score = round(score_s, 1)
            voto_s.confianza = deliberacion_s.get("nueva_confianza", voto_s.confianza)
            voto_s.contra_punto = deliberacion_s.get("contra_punto", voto_s.contra_punto)
            voto_s.tension_con = deliberacion_s.get("tension_con", voto_s.tension_con)

            def _safe_tendencia(v: str) -> str:
                try:
                    TendenciaDim(v)
                    return v
                except ValueError:
                    return "estable"

            evaluacion = EvaluacionNodo(
                nodo_id=nodo_id,
                nodo_nombre=nodo_id.capitalize(),
                dimension_m=voto_m.score,
                dimension_l=voto_l.score,
                dimension_s=voto_s.score,
                justificacion_m=voto_m.justificacion,
                justificacion_l=voto_l.justificacion,
                justificacion_s=voto_s.justificacion,
                tendencia_m=_safe_tendencia(voto_m.tendencia),
                tendencia_l=_safe_tendencia(voto_l.tendencia),
                tendencia_s=_safe_tendencia(voto_s.tendencia),
                score_anterior_m=score_anterior_m,
                score_anterior_l=score_anterior_l,
                score_anterior_s=score_anterior_s,
                votos={"M_m": voto_m, "M_l": voto_l, "M_s": voto_s},
            )
            evaluaciones.append(evaluacion)

        # Árbitro: analizar tensión observacional
        tension_data = self.arbitro.analizar(evaluaciones)
        for ev in evaluaciones:
            for t in tension_data["tensiones_por_nodo"]:
                if t["nodo"] == ev.nodo_id:
                    ev.tension_observacional = t["tension_observacional"]

        vals = [(n.dimension_m, n.dimension_l, n.dimension_s) for n in evaluaciones]
        coh = coherencia_global(vals)

        # Cálculo orbital (diagrama de fase)
        nodos_ml = [n.dimension_l for n in evaluaciones]
        t_cultura = theta_cultura(nodos_ml)
        for n in evaluaciones:
            n.delta = calcular_delta(calcular_angulos(n.dimension_m, n.dimension_l, n.dimension_s))
            n.fragil = n.delta >= 70

        tension = tension_sistema([
            {"dimension_l": n.dimension_l, "dimension_m": n.dimension_m} for n in evaluaciones
        ])
        era_k = 1
        if ultimo_estado:
            era_k = ultimo_estado.era_k + (1 if detectar_vuelco(tension, umbral=800.0) else 0)

        estado = EstadoCultural(
            sociedad=sociedad,
            M_m=round(coh["M_m"], 1),
            M_l=round(coh["M_l"], 1),
            M_s=round(coh["M_s"], 1),
            delta_promedio=round(coh["delta_promedio"], 1),
            coherente=coh["coherente"],
            nodos=evaluaciones,
            nodos_fragiles=[n.nodo_id for n in evaluaciones if n.fragil],
            era_k=era_k,
            theta_cultura=round(t_cultura, 1),
            tension_total=round(tension, 1),
            vuelco_detectado=era_k > (ultimo_estado.era_k if ultimo_estado else 0),
            tension_observacional_promedio=tension_data.get("tension_promedio", 0.0),
            alertas_arbitro=[
                f"[{a.get('nodo','?')}] tensión {a.get('tension',0):.2f}: {a.get('diagnostico','')}"
                for a in tension_data.get("alertas", [])
            ],
        )

        # Formas culturales complejas (e^(2πi / m), m = Σ(v/9.9))
        for dim_key, attr_m, attr_theta in [
            ("m", "m_m", "theta_m"),
            ("l", "m_l", "theta_l"),
            ("s", "m_s", "theta_s"),
        ]:
            vals = [getattr(n, f"dimension_{dim_key}") / 9.9 for n in evaluaciones]
            ft = forma_transversal(vals)
            setattr(estado, attr_m, round(ft["M"], 3))
            setattr(estado, attr_theta, round(math.degrees(ft["angulo"]), 1))
        Fs = [
            forma_cultural_compleja(getattr(estado, f"m_{d}"))
            for d in ("m", "l", "s")
        ]
        estado.coherencia_interna = round(math.degrees(coherencia_formas(Fs)), 1)

        self.store.guardar_estado(estado)
        self.memoria.registrar("observation", f"Observacion {sociedad}: M=({estado.M_m},{estado.M_l},{estado.M_s}) δ={estado.delta_promedio} t_obs={estado.tension_observacional_promedio:.2f}")
        logger.info(f"Observacion completada: delta={estado.delta_promedio:.1f} t_obs={estado.tension_observacional_promedio:.2f}")

        try:
            self.calcular_riesgo(estado, sociedad)
        except Exception as e:
            logger.warning(f"No se pudo calcular riesgo cultural: {e}")

        return estado

    def ciclo_diario(self, sociedad: str = "Chile") -> InformeDiario:
        from topologia.reportes.informe import generar_informe_html

        logger.info("=== CICLO DIARIO ===")

        # PASO 0: Diagnóstico histórico → estrategia de recolección
        estrategia = diagnosticar(sociedad)
        logger.info(
            f"Estrategia: {len(estrategia.nodos_prioritarios)} prioritarios, "
            f"{len(estrategia.nodos_con_brecha)} con brecha, "
            f"umbral de relevancia={estrategia.umbral_relevancia}"
        )

        # PASO 1: Recolección clásica
        items_rss = obtener_items_rss(limite=20)
        items_bcn = obtener_items_bcn(limite=3)
        items_resumen = obtener_items_resumen(limite=10)
        items = items_rss + items_bcn + items_resumen

        items_espectro_b = obtener_items_espectro_b(limite_por_medio=3)
        if items_espectro_b:
            logger.info(f"Espectro B: {len(items_espectro_b)} items")
            items.extend(items_espectro_b)

        items_youtube = buscar_youtube(query="Chile", max_resultados=10)
        if items_youtube:
            logger.info(f"YouTube: {len(items_youtube)} videos")
            items.extend(items_youtube)

        items_tendencias = obtener_tendencias(max_items=10)
        if items_tendencias:
            logger.info(f"Google Trends: {len(items_tendencias)} términos")
            items.extend(items_tendencias)

        # PASO 2: Recolección dirigida por estrategia
        queries = generar_queries(estrategia, max_por_nodo=3)
        items_dirigidos = recolectar_por_queries(queries, estrategia)
        if items_dirigidos:
            logger.info(f"Recolección dirigida: {len(items_dirigidos)} items")
            items.extend(items_dirigidos)

        from topologia.web.rss import filtrar_relevancia_chile
        items = filtrar_relevancia_chile(items)

        # PASO 3: Filtro adaptativo de relevancia (15-20 items finales)
        items = puntuar_relevancia(items, estrategia)
        logger.info(f"Items tras filtro de relevancia: {len(items)}")

        items_por_nodo = self._clasificar_items_por_nodo(items)

        # PASO 4: Scraping dirigido para nodos con déficit persistente
        brechas_iniciales = detectar_brechas(estado=None, items_por_nodo=items_por_nodo)
        from topologia.web.scraping import recolectar_para_brechas
        items_scraping = recolectar_para_brechas(brechas_iniciales)
        if items_scraping:
            logger.info(f"Scraping dirigido: {len(items_scraping)} items adicionales")
            items.extend(items_scraping)
            items = puntuar_relevancia(items, estrategia)
            items_por_nodo = self._clasificar_items_por_nodo(items)

        # PASO 5: Descubrimiento dinámico de fuentes
        # El investigador busca activamente nuevos sitios para nodos prioritarios y con déficit
        nodos_con_brecha = [n for n, c in brechas_iniciales.items() if c.get("items_relevantes", 0) <= 1]
        nodos_a_descubrir = list(set(nodos_con_brecha + estrategia.nodos_prioritarios))
        if nodos_a_descubrir:
            logger.info(f"Descubridor: investigando fuentes para {nodos_a_descubrir}")
            from topologia.web.descubridor import buscar_nuevas_fuentes
            items_descubiertos = buscar_nuevas_fuentes(nodos_a_descubrir, estrategia.nodos_prioritarios)
            if items_descubiertos:
                logger.info(f"Descubrimiento: {len(items_descubiertos)} items de fuentes nuevas")
                items.extend(items_descubiertos)
                items = puntuar_relevancia(items, estrategia)
                items_por_nodo = self._clasificar_items_por_nodo(items)

        paso1 = self.observar(sociedad, items=items)
        operaciones = detectar_operaciones(paso1)

        historial_lista = self._cargar_historial_lista(sociedad, max_dias=7)
        estudios_previos = self._cargar_estudios_recientes()
        especulaciones = self.artista.especular(
            items, estado=paso1,
            historial=historial_lista,
            estudios_previos=estudios_previos,
        )

        estudios = self._investigar_preguntas(especulaciones, paso1)

        historial = self._obtener_historial_reciente(sociedad)
        if paso1.tension_observacional_promedio > 0:
            historial += f"\n\nTensión observacional promedio: {paso1.tension_observacional_promedio:.2f}"
            for a in paso1.alertas_arbitro:
                historial += f"\n- [Árbitro] {a}"

        informe_anterior = self._cargar_informe_anterior(sociedad)

        analisis_formas = self._analizar_formas_complejas(paso1)
        graficos = [
            "grafico_plano_complejo.png",
            "grafico_rotacion_angular.png",
            "grafico_triangulo_coherencia.png",
            "grafico_radar_nodos.png",
            "grafico_mapa_calor_nodos.png",
        ]
        informe = self.redactor.sintetizar(
            paso1, operaciones, especulaciones, estudios, historial,
            analisis_formas=analisis_formas,
            graficos_generados=graficos,
            informe_anterior=informe_anterior,
        )

        self._guardar_informe(sociedad, informe)

        brechas = detectar_brechas(estado=paso1, items_por_nodo=items_por_nodo)
        resumen = resumen_brechas(brechas)
        logger.info(f"Cobertura de datos: {resumen}")
        if items_scraping:
            logger.info(f"Items de scraping: {len(items_scraping)} (incluidos en cobertura)")
        informe.resumen_ejecutivo = (informe.resumen_ejecutivo or "") + f"\n\n[COBERTURA] {resumen}"

        try:
            from scripts.analisis_graficos import generar_todos
            generar_todos(sociedad, items_por_nodo=items_por_nodo)
            logger.info("Gráficos diarios generados")
        except Exception as e:
            logger.warning(f"No se pudieron generar gráficos diarios: {e}")

        # Tromba y tecelado del ente fractal
        try:
            from scripts.visualizar_tromba_tecelado import generar_todos as generar_tromba
            generar_tromba(sociedad)
            logger.info("Tromba y tecelado generados")
        except Exception as e:
            logger.warning(f"No se pudo generar la tromba/tecelado: {e}")

        # Timeline: actualizar data y regenerar gráficos de evolución
        try:
            from scripts.barrido_timeline import actualizar_timeline
            actualizar_timeline(sociedad)
            from scripts.graficos_timeline import generar_todos as generar_timeline
            generar_timeline(items_por_nodo=items_por_nodo)
            logger.info("Timeline y gráficos de evolución actualizados")
        except Exception as e:
            logger.warning(f"No se pudo actualizar timeline: {e}")

        ruta_informe = generar_informe_html(
            sociedad=sociedad,
            estado=paso1,
            operaciones=operaciones,
            especulaciones=especulaciones,
            estudios=estudios,
            items_por_nodo=items_por_nodo,
            informe_redactor=informe,
            brechas=brechas,
        )
        logger.info(f"Informe generado: {ruta_informe}")
        logger.info(f"Resumen: {informe.resumen_ejecutivo}")
        try:
            destino = Path.home() / "Desktop" / "informe_topologia.html"
            shutil.copy2(ruta_informe, destino)
            logger.info(f"Copia en escritorio: {destino}")
        except Exception as e:
            logger.warning(f"No se pudo copiar informe al escritorio: {e}")

        # Aprendizaje persistente: rendimiento de fuentes
        try:
            self._actualizar_rendimiento_fuentes(items_por_nodo)
        except Exception as e:
            logger.warning(f"No se pudo actualizar rendimiento de fuentes: {e}")

        return informe

    def _clasificar_items_por_nodo(self, items: list) -> dict[str, list]:
        return clasificar_items_por_nodo_semantico(items)

    def _actualizar_rendimiento_fuentes(self, items_por_nodo: dict[str, list]):
        import yaml
        from pathlib import Path
        from collections import Counter

        ruta = Path(__file__).resolve().parent.parent.parent / "data" / "rendimiento_fuentes.yaml"
        rendimiento: dict = {}
        if ruta.exists():
            with open(ruta, encoding="utf-8") as f:
                rendimiento = yaml.safe_load(f) or {}

        fuente_nodos: dict[str, Counter] = {}
        for nodo_id, nodo_items in items_por_nodo.items():
            for it in nodo_items:
                fuente = (it.fuente or "desconocida").lower()
                if fuente not in fuente_nodos:
                    fuente_nodos[fuente] = Counter()
                fuente_nodos[fuente][nodo_id] += 1

        for fuente, nodos in fuente_nodos.items():
            if fuente not in rendimiento:
                rendimiento[fuente] = {"total_items": 0, "items_por_nodo": {}}
            rendimiento[fuente]["total_items"] += sum(nodos.values())
            for nid, count in nodos.items():
                prev = rendimiento[fuente]["items_por_nodo"].get(nid, 0)
                rendimiento[fuente]["items_por_nodo"][nid] = prev + count

        for fuente, data in rendimiento.items():
            total = data.get("total_items", 0) or 1
            relevantes = sum(data.get("items_por_nodo", {}).values())
            data["proporcion_relevantes"] = round(relevantes / total, 2)

        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            yaml.dump(rendimiento, f, default_flow_style=False, allow_unicode=True)
        logger.debug(f"Rendimiento de fuentes actualizado en {ruta}")

    def _investigar_preguntas(self, especulaciones: list, estado: EstadoCultural) -> list[Estudio]:
        estudios: list[Estudio] = []
        for esp in especulaciones:
            try:
                patron = self.memoria.patron_por_id(esp.patron_id)
                if patron is None:
                    patron_info = {"forma": "", "significado": ""}
                else:
                    patron_info = {"forma": patron.forma, "significado": patron.significado}

                query = esp.pregunta_abierta or esp.argumento[:100]
                items_busqueda = buscar_para_estudio(esp.patron_id, query)

                analisis_m = self.estadista.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    argumento_artista=esp.argumento,
                    pregunta_abierta=esp.pregunta_abierta,
                )
                analisis_l = self.filosofo.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    argumento_artista=esp.argumento,
                    pregunta_abierta=esp.pregunta_abierta,
                )
                analisis_s = self.sociologo.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    argumento_artista=esp.argumento,
                    pregunta_abierta=esp.pregunta_abierta,
                )

                hallazgos = [a.hallazgo for a in [analisis_m, analisis_l, analisis_s] if a.hallazgo]
                respuesta = " | ".join(hallazgos) if hallazgos else "Sin hallazgos concluyentes"
                confianzas = [a.confianza for a in [analisis_m, analisis_l, analisis_s]]
                tension_latente = all(c < 0.5 for c in confianzas) and bool(esp.pregunta_abierta)

                if tension_latente:
                    self.memoria.registrar("pattern",
                        f"Tensión latente: {esp.pregunta_abierta}",
                        tags=[esp.patron_id])

                estudio = Estudio(
                    id=f"EST-{len(estudios)+1:04d}",
                    especulacion_id=esp.id,
                    patron_id=esp.patron_id,
                    pregunta_investigada=esp.pregunta_abierta,
                    respuesta=respuesta,
                    tension_latente=tension_latente,
                    items_originales=esp.items_relacionados,
                    items_investigacion=[it.id for it in items_busqueda],
                    analisis={
                        "M_m": analisis_m,
                        "M_l": analisis_l,
                        "M_s": analisis_s,
                    },
                )
                estudios.append(estudio)
                tag = "TENSIÓN LATENTE" if tension_latente else "investigado"
                logger.info(f"Estudio {estudio.id}: {esp.patron_id} → {tag}")

            except Exception as e:
                logger.error(f"Error en estudio de {esp.patron_id}: {e}")

        return estudios

    def _analizar_formas_complejas(self, estado_actual: EstadoCultural) -> str:
        """Compara las formas complejas del estado actual vs el anterior."""
        fechas = self.store.listar_estados(estado_actual.sociedad)
        anterior = self.store.cargar_estado(
            estado_actual.sociedad,
            fecha=fechas[-2] if len(fechas) >= 2 else None,
        )

        lineas = ["=== ANÁLISIS DE FORMAS COMPLEJAS (e^(2πi / m)) ==="]

        for dim, nombre in [("m", "M_m"), ("l", "M_l"), ("s", "M_s")]:
            m_act = getattr(estado_actual, f"m_{dim}")
            th_act = getattr(estado_actual, f"theta_{dim}")

            if anterior:
                m_ant = getattr(anterior, f"m_{dim}")
                th_ant = getattr(anterior, f"theta_{dim}")
                delta_th = abs(th_act - th_ant)
                dir_str = {"m": "↻ horario", "l": "↺ antihorario", "s": "→ estable"}[
                    "m" if th_act >= th_ant else "l"
                ]
                lineas.append(
                    f"- {nombre}: M={m_ant:.3f}\u2192M\u2032={m_act:.3f}  "
                    f"\u03b8 {th_ant:.1f}\u00b0\u2192{th_act:.1f}\u00b0  "
                    f"\u0394\u03b8={delta_th:.1f}\u00b0 ({dir_str})"
                )
            else:
                lineas.append(f"- {nombre}: M={m_act:.3f} \u03b8={th_act:.1f}\u00b0 (sin ref. anterior)")

        lineas.append(
            f"- Coherencia interna: {estado_actual.coherencia_interna:.1f}° "
            f"entre las 3 formas (bajo = coherente)"
        )

        diffs = {
            "M_m↔M_l": abs(estado_actual.theta_m - estado_actual.theta_l),
            "M_l↔M_s": abs(estado_actual.theta_l - estado_actual.theta_s),
            "M_s↔M_m": abs(estado_actual.theta_s - estado_actual.theta_m),
        }
        max_pair = max(diffs, key=diffs.get)
        lineas.append(f"- Mayor divergencia: {max_pair} = {diffs[max_pair]:.1f}°")

        return "\n".join(lineas)

    def _obtener_historial_reciente(self, sociedad: str) -> str:
        fechas = self.store.listar_estados(sociedad)
        fechas = fechas[-7:]
        if not fechas:
            return ""
        partes = []
        for f in fechas:
            estado = self.store.cargar_estado(sociedad, f)
            if estado:
                partes.append(f"- {f}: δ={estado.delta_promedio:.1f}° M=({estado.M_m:.1f},{estado.M_l:.1f},{estado.M_s:.1f})")
        return "\n".join(partes)

    def _cargar_historial_lista(self, sociedad: str, max_dias: int = 7) -> list:
        fechas = self.store.listar_estados(sociedad)
        fechas = fechas[-max_dias:]
        estados = []
        for f in fechas:
            estado = self.store.cargar_estado(sociedad, f)
            if estado:
                estados.append(estado)
        return estados

    def _guardar_informe(self, sociedad: str, informe) -> None:
        fecha = informe.fecha.strftime("%Y-%m-%d")
        self.store.guardar_json(
            f"reportes_json/{sociedad}_{fecha}.json",
            informe.model_dump(mode="json"),
        )

    def _cargar_informe_anterior(self, sociedad: str) -> str:
        base = self.store.base / "reportes_json"
        if not base.exists():
            return ""
        archivos = sorted(base.glob(f"{sociedad}_*.json"))
        if len(archivos) < 2:
            return ""
        data = json.loads(archivos[-2].read_text(encoding="utf-8"))
        partes = []
        for campo in ("panorama", "dinamicas", "especulaciones_y_estudios", "mirada_adelante"):
            val = data.get(campo, "")
            if val:
                label = campo.replace("_", " ").title()
                partes.append(f"=== {label} ===\n{val[:500]}")
        return "\n\n".join(partes) if partes else ""

    def _cargar_estudios_recientes(self, max_dias: int = 7) -> list:
        estudios = []
        base = self.store.base / "estudios"
        if not base.exists():
            return estudios
        archivos = sorted(base.glob("*.txt"), key=os.path.getmtime, reverse=True)
        for a in archivos[:max_dias]:
            try:
                from topologia.models.schemas import Estudio
                contenido = a.read_text(encoding="utf-8")
                estudio = Estudio(
                    id=f"EST-HIST-{a.stem}",
                    especulacion_id="",
                    patron_id=a.stem.replace("estudio_", "").replace("_", " ").title(),
                    pregunta_investigada=contenido[:100],
                    respuesta=contenido[:500],
                )
                estudios.append(estudio)
            except Exception:
                continue
        return estudios

    def calibrar(self, estado: EstadoCultural, ruta_hitos: str | Path | None = None) -> dict:
        """Compara el estado cultural actual contra hitos históricos.
        Retorna ranking de similitud + hito más cercano.

        Args:
            estado: EstadoCultural actual (con nodos con delta)
            ruta_hitos: path a hitos.yaml (default: config/hitos.yaml)

        Returns:
            dict con 'mas_similar', 'ranking' (lista ordenada por correlación),
            'cluster', 'nodos_destacados'
        """
        import yaml
        from math import sqrt

        if ruta_hitos is None:
            ruta_hitos = Path(__file__).resolve().parent.parent.parent / "config" / "hitos.yaml"
        if not Path(ruta_hitos).exists():
            return {"mas_similar": None, "ranking": [], "cluster": "sin_datos"}

        hitos: list[dict] = yaml.safe_load(open(ruta_hitos, encoding="utf-8")) or []
        if not hitos:
            return {"mas_similar": None, "ranking": [], "cluster": "sin_hitos"}

        NODOS = ["ECONOMIA","TRABAJO","SEXUALIDAD","POLITICA","LENGUAJE",
                 "ETICA_ESTETICA","TECNOLOGIA","EDUCACION","RELIGION"]
        actual = {n.nodo_id: n.delta for n in estado.nodos}

        resultados = []
        for hito in hitos:
            fingerprint = {n: hito["nodos"][n]["delta"] for n in NODOS}
            va = [actual.get(n, 0) for n in NODOS]
            vh = [fingerprint[n] for n in NODOS]
            ma = sum(va) / len(va)
            mh = sum(vh) / len(vh)
            num = sum((va[k] - ma) * (vh[k] - mh) for k in range(9))
            den = sqrt(sum((va[k] - ma) ** 2 for k in range(9)) * sum((vh[k] - mh) ** 2 for k in range(9)))
            r = num / den if den else 0
            mae = sum(abs(va[k] - vh[k]) for k in range(9)) / 9
            resultados.append({
                "id": hito["id"],
                "descripcion": hito.get("descripcion", ""),
                "periodo": f"{hito['periodo']['inicio']} - {hito['periodo']['fin']}",
                "correlacion": round(r, 3),
                "mae": round(mae, 2),
                "delta_hito": hito["estado"]["delta_promedio"],
                "delta_actual": round(estado.delta_promedio, 1),
            })

        resultados.sort(key=lambda x: x["correlacion"], reverse=True)

        mas_similar = resultados[0] if resultados else None
        cluster = self._clasificar_cluster(mas_similar["id"] if mas_similar else None)

        nodos_destacados = []
        if mas_similar:
            hito = next((x for x in hitos if x["id"] == mas_similar["id"]), None)
            if hito:
                for n in NODOS:
                    dif = actual.get(n, 0) - hito["nodos"][n]["delta"]
                    if abs(dif) > 3:
                        nodos_destacados.append({
                            "nodo": n,
                            "delta_actual": round(actual.get(n, 0), 1),
                            "delta_hito": round(hito["nodos"][n]["delta"], 1),
                            "diferencia": round(dif, 1),
                            "etiqueta": "ALERTA" if abs(dif) > 5 else "DIFERENCIA"
                        })

        return {
            "mas_similar": mas_similar,
            "ranking": resultados,
            "cluster": cluster,
            "nodos_destacados": nodos_destacados,
        }

    def calcular_riesgo(self, estado: EstadoCultural, sociedad: str = "Chile") -> dict:
        from topologia.escalar.compuesto import calcular_riesgo as _calc
        from topologia.escalar.red_riesgo import exportar_red

        historial = self._cargar_historial_lista(sociedad, max_dias=14)
        riesgo = _calc(estado, historial=historial)

        ruta_red = exportar_red(riesgo, estado, historial=historial)

        res = riesgo.a_dict()
        res["ruta_red"] = str(ruta_red)
        res["historial_tam"] = len(historial)

        logger.info(f"Riesgo cultural: R={riesgo.R_compuesto:.3f} ({riesgo.alerta}) — red: {ruta_red.name}")

        self.store.guardar_json("riesgo_actual.json", res)

        return res

    @staticmethod
    def _clasificar_cluster(hito_id: str | None) -> str:
        if hito_id is None:
            return "desconocido"
        cluster_a = {"estallido_nocturno_2020", "plebiscito_2020", "temporal_julio_2026", "pandemia_ola2_2021"}
        cluster_b = {"plebiscito_1988", "estallido_2019", "pandemia_ola1_2020"}
        if hito_id in cluster_a:
            return "crisis_reciente (post-2020)"
        if hito_id in cluster_b:
            return "crisis_fundacional (pre-2020)"
        return "indeterminado"
