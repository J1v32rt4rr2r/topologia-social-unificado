from __future__ import annotations

from datetime import datetime

from topologia.agents.artista import Artista
from topologia.agents.estadista import Estadista
from topologia.agents.filosofo import Filosofo
from topologia.agents.redactor import Redactor
from topologia.agents.sociologo import Sociologo
from topologia.logger import logger
from topologia.math.operations import detectar_operaciones
from topologia.math.torus import calcular_angulos, calcular_delta, coherencia_global
from topologia.memoria.decisiones import DecisionDB
from topologia.models.schemas import (
    EstadoCultural,
    EstadoPatron,
    Estudio,
    EvaluacionNodo,
)
from topologia.storage.store import FileStore
from topologia.web.rss import obtener_items
from topologia.web.search import buscar_para_estudio


NODOS_CULTURALES = [
    "ECONOMIA", "TRABAJO", "CONTINUIDAD", "POLITICA",
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

    def observar(self, sociedad: str = "Chile") -> EstadoCultural:
        logger.info(f"Iniciando observación: {sociedad}")
        items = obtener_items(limite=30)

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

            items_filtrados = [it for it in items if nodo_id.lower() in (it.titulo + it.contenido).lower()]
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
            angulos = calcular_angulos(eval_m.dimension_m, eval_l.dimension_l, eval_s.dimension_s)
            evaluacion.delta = calcular_delta(angulos)
            evaluacion.fragil = evaluacion.delta >= 70
            evaluaciones.append(evaluacion)

        vals = [(n.dimension_m, n.dimension_l, n.dimension_s) for n in evaluaciones]
        coh = coherencia_global(vals)

        estado = EstadoCultural(
            sociedad=sociedad,
            M_m=round(coh["M_m"], 1),
            M_l=round(coh["M_l"], 1),
            M_s=round(coh["M_s"], 1),
            delta_promedio=round(coh["delta_promedio"], 1),
            coherente=coh["coherente"],
            nodos=evaluaciones,
            nodos_fragiles=[n.nodo_id for n in evaluaciones if n.fragil],
        )

        self.store.guardar_estado(estado)
        self.memoria.registrar("observation", f"Observacion {sociedad}: M=({estado.M_m}, {estado.M_l}, {estado.M_s}), delta={estado.delta_promedio}")
        logger.info(f"Observacion completada: delta={estado.delta_promedio:.1f}")

        return estado

    def ciclo_diario(self, sociedad: str = "Chile") -> InformeDiario:
        from topologia.reportes.informe import generar_informe

        logger.info("=== CICLO DIARIO ===")

        items = obtener_items(limite=20)
        items_por_nodo = self._clasificar_items_por_nodo(items)

        paso1 = self.observar(sociedad)
        operaciones = detectar_operaciones(paso1)

        especulaciones = self.artista.especular(items)

        estudios = self._ejecutar_estudios(especulaciones, paso1)

        historial = self._obtener_historial_reciente(sociedad)
        informe = self.redactor.sintetizar(paso1, operaciones, especulaciones, estudios, historial)

        ruta_informe = generar_informe(
            sociedad=sociedad,
            estado=paso1,
            operaciones=operaciones,
            especulaciones=especulaciones,
            estudios=estudios,
            items_por_nodo=items_por_nodo,
            informe_redactor=informe,
        )
        logger.info(f"Informe generado: {ruta_informe}")
        logger.info(f"Resumen: {informe.resumen_ejecutivo}")

        return informe

    def _clasificar_items_por_nodo(self, items: list) -> dict[str, list]:
        mapa: dict[str, list] = {}
        for nodo_id in NODOS_CULTURALES:
            filtrados = [it for it in items if nodo_id.lower() in (it.titulo + it.contenido).lower()]
            mapa[nodo_id] = filtrados or items[:3]
        return mapa

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
                )
                analisis_s = self.sociologo.validar_estudio(
                    items_busqueda,
                    patron_id=esp.patron_id,
                    forma_patron=patron_info["forma"],
                    significado_patron=patron_info["significado"],
                    items_originales=", ".join(esp.items_relacionados),
                    argumento_artista=esp.argumento,
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
