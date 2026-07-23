from __future__ import annotations

import math
import shutil
from pathlib import Path

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
    EstadoPatron,
    Estudio,
    EvaluacionNodo,
    InformeDiario,
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
            items_filtrados = [
                it for it in items
                if any(t in (it.titulo + it.contenido).lower() for t in terminos)
            ]
            items_filtrados = items_filtrados or items[:5]

            eval_m = self.estadista.evaluar_nodo(nodo_id, items_filtrados, score_anterior_m, just_anterior_m)
            eval_l = self.filosofo.evaluar_nodo(nodo_id, items_filtrados, score_anterior_l, just_anterior_l)
            eval_s = self.sociologo.evaluar_nodo(nodo_id, items_filtrados, score_anterior_s, just_anterior_s)

            evaluacion = EvaluacionNodo(
                nodo_id=nodo_id,
                nodo_nombre=nodo_id.capitalize(),
                dimension_m=eval_m.dimension_m,
                dimension_l=eval_l.dimension_l,
                dimension_s=eval_s.dimension_s,
                justificacion_m=eval_m.justificacion_m,
                justificacion_l=eval_l.justificacion_l,
                justificacion_s=eval_s.justificacion_s,
                tendencia_m=eval_m.tendencia_m,
                tendencia_l=eval_l.tendencia_l,
                tendencia_s=eval_s.tendencia_s,
                score_anterior_m=score_anterior_m,
                score_anterior_l=score_anterior_l,
                score_anterior_s=score_anterior_s,
            )
            evaluaciones.append(evaluacion)

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
        self.memoria.registrar("observation", f"Observacion {sociedad}: M=({estado.M_m},{estado.M_l},{estado.M_s}) δ={estado.delta_promedio} m=({estado.m_m},{estado.m_l},{estado.m_s}) θ=({estado.theta_m}°,{estado.theta_l}°,{estado.theta_s}°)")
        logger.info(f"Observacion completada: delta={estado.delta_promedio:.1f}")

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

        especulaciones = self.artista.especular(items)

        estudios = self._ejecutar_estudios(especulaciones, paso1)

        historial = self._obtener_historial_reciente(sociedad)
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
        )

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

    def _ejecutar_estudios(self, especulaciones: list, estado: EstadoCultural) -> list[Estudio]:
        estudios: list[Estudio] = []
        for esp in especulaciones:
            try:
                patron = self.memoria.patron_por_id(esp.patron_id)
                if patron is None:
                    patron_info = {"forma": "", "significado": ""}
                else:
                    patron_info = {"forma": patron.forma, "significado": patron.significado}

                items_busqueda = buscar_para_estudio(esp.patron_id, esp.argumento[:100])

                analisis_m = self.estadista.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    items_originales=", ".join(esp.items_relacionados),
                    argumento_artista=esp.argumento,
                    confianza_artista=str(esp.confianza),
                )
                analisis_l = self.filosofo.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    items_originales=", ".join(esp.items_relacionados),
                    argumento_artista=esp.argumento,
                    confianza_artista=str(esp.confianza),
                )
                analisis_s = self.sociologo.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    items_originales=", ".join(esp.items_relacionados),
                    argumento_artista=esp.argumento,
                    confianza_artista=str(esp.confianza),
                )

                confirmados = [a.confirmado for a in [analisis_m, analisis_l, analisis_s]]
                todos_ok = all(confirmados)
                ninguno_ok = not any(confirmados)
                if todos_ok:
                    veredicto = "validado"
                    estado_patron = EstadoPatron.validado
                elif ninguno_ok:
                    veredicto = "refutado"
                    estado_patron = EstadoPatron.refutado
                else:
                    veredicto = "parcial"
                    estado_patron = EstadoPatron.parcial

                self.memoria.validar_patron(esp.patron_id, estado_patron)
                self.memoria.registrar("pattern", f"Estudio {esp.patron_id}: {veredicto}", tags=[esp.patron_id])

                estudio = Estudio(
                    id=f"EST-{len(estudios)+1:04d}",
                    especulacion_id=esp.id,
                    patron_id=esp.patron_id,
                    estado=estado_patron,
                    items_originales=esp.items_relacionados,
                    items_investigacion=[it.id for it in items_busqueda],
                    analisis={
                        "M_m": analisis_m,
                        "M_l": analisis_l,
                        "M_s": analisis_s,
                    },
                    veredicto=veredicto,
                )
                estudios.append(estudio)
                logger.info(f"Estudio {estudio.id}: {esp.patron_id} → {veredicto}")

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
