from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from topologia.logger import logger
from topologia.memoria.bloques import BloquesMemoria
from topologia.memoria.decisiones import DecisionDB
from topologia.models.llm import LLMClient
from topologia.prompts import PromptLoader


BLOQUES_PIPELINE = ["analogia-termica", "analogia-visual", "analogia-cinetica", "analogia-emergente"]


@dataclass
class ResultadoPipeline:
    texto: str
    nombre_texto: str
    timestamp: datetime = field(default_factory=datetime.now)
    fase1: dict | None = None
    fase2: dict | None = None
    fase3: dict | None = None
    fase4: dict | None = None
    fase5: dict | None = None
    fase6: dict | None = None
    error: str | None = None

    def resumen(self) -> str:
        partes = [f"Pipeline: {self.nombre_texto}"]
        if self.fase1:
            partes.append(f"  F1: estructura={self.fase1.get('estructura_superficial', {}).get('genero', '?')}")
        if self.fase2:
            op = self.fase2.get("nueva_operacion_cinetica", "") or self.fase2.get("metafora_visual_primaria", "")[:60]
            partes.append(f"  F2: {op}")
        if self.fase3:
            op_dom = self.fase3.get("operacion_cinetica_dominante", {})
            partes.append(f"  F3: dominante={op_dom.get('codigo', '?')} intensidad={op_dom.get('intensidad', 0)}")
        if self.fase4:
            desv = len(self.fase4.get("desviaciones", []))
            partes.append(f"  F4: {desv} desviaciones")
        if self.fase5:
            ems = len(self.fase5.get("emergencias", []))
            partes.append(f"  F5: {ems} emergencias")
        if self.fase6:
            reglas = len(self.fase6.get("reglas_formales", []))
            axiomas = len(self.fase6.get("axiomas", []))
            partes.append(f"  F6: {reglas} reglas, {axiomas} axiomas")
        if self.error:
            partes.append(f"  ERROR: {self.error}")
        return "\n".join(partes)


class Pipeline:
    def __init__(self):
        self.llm = LLMClient()
        self.prompts = PromptLoader()
        self.memoria = BloquesMemoria()
        self.decisions = DecisionDB()
        self._contador_emergencias = self._proximo_id_emergencia()
        self._contador_decisiones = len(self.decisions.listar())

    def _proximo_id_emergencia(self) -> int:
        existentes = self.memoria.listar()
        max_n = 0
        for nombre in existentes:
            contenido = self.memoria.leer(nombre)
            for line in contenido.splitlines():
                if "emergente-" in line:
                    try:
                        n = int(line.split("emergente-")[1].split('"')[0].split(":")[0].strip())
                        max_n = max(max_n, n)
                    except (ValueError, IndexError):
                        pass
        return max_n + 1

    def _cargar_config(self) -> dict:
        ruta = Path(__file__).resolve().parent.parent.parent.parent / "mmcp" / "analogic-config.json"
        if ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))
        return {}

    def _leer_bloques_memoria(self, nombres: list[str]) -> dict[str, str]:
        resultado = {}
        for nombre in nombres:
            contenido = self.memoria.leer(nombre)
            if contenido:
                resultado[nombre] = contenido[:2000]
            else:
                resultado[nombre] = "(vacio)"
        return resultado

    def _registrar_decision(self, tipo: str, contenido: str, tags: list[str] | None = None):
        self._contador_decisiones += 1
        self.decisions.registrar(tipo, contenido, tags=tags)

    def ejecutar(self, ruta_texto: str) -> ResultadoPipeline:
        texto_path = Path(ruta_texto)
        if not texto_path.exists():
            return ResultadoPipeline(texto="", nombre_texto=ruta_texto, error=f"Archivo no encontrado: {ruta_texto}")

        texto = texto_path.read_text(encoding="utf-8")
        nombre = texto_path.stem
        resultado = ResultadoPipeline(texto=texto, nombre_texto=nombre)
        config = self._cargar_config()

        logger.info(f"=== PIPELINE: {nombre} ===")

        try:
            resultado.fase1 = self._fase1_inmersion(texto, nombre, config)
            logger.info("Fase 1 completa")

            resultado.fase2 = self._fase2_pictorica(resultado, config)
            logger.info("Fase 2 completa")

            resultado.fase3 = self._fase3_analisis(resultado, config)
            logger.info("Fase 3 completa")

            resultado.fase4 = self._fase4_reescritura(resultado, config)
            logger.info("Fase 4 completa")

            resultado.fase5 = self._fase5_emergencias(resultado, config)
            logger.info("Fase 5 completa")

            resultado.fase6 = self._fase6_formalizacion(resultado, config)
            logger.info("Fase 6 completa")

            self._guardar_resultado(resultado)

        except Exception as e:
            logger.error(f"Pipeline falló en {nombre}: {e}")
            resultado.error = str(e)

        return resultado

    def _ejecutar_fase(self, prompt_name: str, variables: dict, temperatura: float, max_tokens: int = 2048) -> dict:
        prompt = self.prompts.load(prompt_name, **variables)
        try:
            return self.llm.generar_json(prompt, temperatura=temperatura, max_tokens=max_tokens)
        except Exception as e:
            logger.error(f"Error en fase {prompt_name}: {e}")
            return {"error": str(e)}

    def _fase1_inmersion(self, texto: str, nombre: str, config: dict) -> dict:
        cfg = config.get("fases", {}).get("inmersion", {})
        memoria_termica = self.memoria.leer("analogia-termica") or "(sin contenido)"
        decisiones_previas = self._formatear_decisiones_para_prompt()

        resultado = self._ejecutar_fase("pipeline_f1_inmersion", {
            "texto_fuente": texto,
            "nombre_texto": nombre,
            "memoria_termica": memoria_termica[:1500],
            "decisiones_previas": decisiones_previas,
        }, temperatura=cfg.get("temperatura", 0.5), max_tokens=cfg.get("max_tokens", 2048))

        self.memoria.escribir("analogia-termica",
            f"# {nombre}\n\n{resultado.get('resumen_para_fase2', resultado.get('nucleo_semantico', ''))}")
        self._registrar_decision("observation",
            f"F1-{nombre}: {resultado.get('nucleo_semantico', '')[:200]}",
            tags=[nombre, "fase1"])

        return resultado

    def _fase2_pictorica(self, r: ResultadoPipeline, config: dict) -> dict:
        cfg = config.get("fases", {}).get("pictorica", {})
        temp = r.fase1.get("temperatura_sugerida", cfg.get("temperatura", 0.65)) if r.fase1 else cfg.get("temperatura", 0.65)
        memorias = self._leer_bloques_memoria(cfg.get("bloques_memoria", ["analogia-visual", "analogia-cinetica", "analogia-emergente"]))

        resultado = self._ejecutar_fase("pipeline_f2_pictorica", {
            "analisis_f1": json.dumps(r.fase1, indent=2),
            "nombre_texto": r.nombre_texto,
            "memoria_visual": memorias.get("analogia-visual", "(vacio)"),
            "memoria_cinetica": memorias.get("analogia-cinetica", "(vacio)"),
            "memoria_emergente": memorias.get("analogia-emergente", "(vacio)"),
            "temperatura": str(temp),
        }, temperatura=temp, max_tokens=cfg.get("max_tokens", 2048))

        visual_update = resultado.get("nueva_contribucion_visual", "")
        if visual_update:
            existing = self.memoria.leer("analogia-visual")
            self.memoria.escribir("analogia-visual", f"{existing}\n\n## {r.nombre_texto}\n{visual_update}")

        op_nueva = resultado.get("nueva_operacion_cinetica", "")
        if op_nueva:
            existing = self.memoria.leer("analogia-cinetica")
            self.memoria.escribir("analogia-cinetica", f"{existing}\n\n## {r.nombre_texto}\n{op_nueva}")

        self._registrar_decision("pattern",
            f"F2-{r.nombre_texto}: {resultado.get('metafora_visual_primaria', '')[:200]}",
            tags=[r.nombre_texto, "fase2", "visual"])

        return resultado

    def _fase3_analisis(self, r: ResultadoPipeline, config: dict) -> dict:
        cfg = config.get("fases", {}).get("analisis", {})
        memorias = self._leer_bloques_memoria(cfg.get("bloques_memoria", ["analogia-cinetica", "analogia-visual", "analogia-emergente"]))

        resultado = self._ejecutar_fase("pipeline_f3_analisis", {
            "descripcion_f2": json.dumps(r.fase2, indent=2),
            "nombre_texto": r.nombre_texto,
            "memoria_cinetica": memorias.get("analogia-cinetica", "(vacio)"),
            "decisiones_previas": self._formatear_decisiones_para_prompt(),
            "memoria_emergente": memorias.get("analogia-emergente", "(vacio)"),
        }, temperatura=cfg.get("temperatura", 0.25), max_tokens=cfg.get("max_tokens", 2048))

        op_dom = resultado.get("operacion_cinetica_dominante", {})
        codigo = op_dom.get("codigo", "O??")
        self._registrar_decision("pattern",
            f"F3-{r.nombre_texto}: operación dominante {codigo}",
            tags=[r.nombre_texto, "fase3", "cinetica", codigo])

        return resultado

    def _fase4_reescritura(self, r: ResultadoPipeline, config: dict) -> dict:
        cfg = config.get("fases", {}).get("reescritura", {})
        memoria_emergente = self.memoria.leer("analogia-emergente") or "(sin contenido)"

        resultado = self._ejecutar_fase("pipeline_f4_reescritura", {
            "texto_fuente": r.texto,
            "descripcion_f2": json.dumps(r.fase2, indent=2),
            "analisis_f3": json.dumps(r.fase3, indent=2),
            "nombre_texto": r.nombre_texto,
            "memoria_emergente": memoria_emergente[:2000],
        }, temperatura=cfg.get("temperatura", 0.5), max_tokens=cfg.get("max_tokens", 2048))

        desviaciones = resultado.get("desviaciones", [])
        if desviaciones:
            self._registrar_decision("pattern",
                f"F4-{r.nombre_texto}: {len(desviaciones)} desviaciones detectadas",
                tags=[r.nombre_texto, "fase4", "reescritura"])

        return resultado

    def _fase5_emergencias(self, r: ResultadoPipeline, config: dict) -> dict:
        cfg = config.get("fases", {}).get("emergencias", {})
        vault_emergencias = self.memoria.leer("analogia-emergente") or "(sin emergencias previas)"

        resultado = self._ejecutar_fase("pipeline_f5_emergencias", {
            "analisis_f1": json.dumps(r.fase1, indent=2),
            "reescritura_f4": json.dumps(r.fase4, indent=2),
            "nombre_texto": r.nombre_texto,
            "vault_emergencias": vault_emergencias[:2000],
        }, temperatura=cfg.get("temperatura", 0.4), max_tokens=cfg.get("max_tokens", 2048))

        emergencias = resultado.get("emergencias", [])
        for i, em in enumerate(emergencias):
            em_id = f"emergente-{self._contador_emergencias + i:03d}"
            em["id"] = em_id
            entry = (
                f"---\n"
                f"id: {em_id}\n"
                f"sesion: {r.nombre_texto}\n"
                f"tipo: {em.get('tipo', 'descubrimiento')}\n"
                f"tags: [#emergente, {r.nombre_texto}]\n"
                f"---\n\n"
                f"# {em.get('titulo', 'Emergencia')}\n\n"
                f"{em.get('descripcion', '')}\n"
            )
            existing = self.memoria.leer("analogia-emergente")
            self.memoria.escribir("analogia-emergente", f"{existing}\n\n{entry}")

        self._contador_emergencias += len(emergencias)
        return resultado

    def _fase6_formalizacion(self, r: ResultadoPipeline, config: dict) -> dict:
        cfg = config.get("fases", {}).get("formalizacion", {})
        decisiones_previas = self._formatear_decisiones_para_prompt()

        resultado = self._ejecutar_fase("pipeline_f6_formalizacion", {
            "analisis_f1": json.dumps(r.fase1, indent=2),
            "descripcion_f2": json.dumps(r.fase2, indent=2),
            "analisis_f3": json.dumps(r.fase3, indent=2),
            "reescritura_f4": json.dumps(r.fase4, indent=2),
            "emergencias_f5": json.dumps(r.fase5, indent=2),
            "nombre_texto": r.nombre_texto,
            "decisiones_previas": decisiones_previas,
        }, temperatura=cfg.get("temperatura", 0.3), max_tokens=cfg.get("max_tokens", 2048))

        for leccion in resultado.get("lecciones", []):
            contenido = leccion.get("contenido", "")
            tags = leccion.get("tags", []) + [r.nombre_texto, "formalizacion"]
            self._registrar_decision("lesson", contenido, tags=tags)

        visual_resumen = resultado.get("resumen_memoria_visual", "")
        if visual_resumen:
            existing = self.memoria.leer("analogia-visual")
            self.memoria.escribir("analogia-visual", f"{existing}\n\n### Formalización {r.nombre_texto}\n{visual_resumen}")

        cinetica_resumen = resultado.get("resumen_memoria_cinetica", "")
        if cinetica_resumen:
            existing = self.memoria.leer("analogia-cinetica")
            self.memoria.escribir("analogia-cinetica", f"{existing}\n\n### Formalización {r.nombre_texto}\n{cinetica_resumen}")

        emergente_resumen = resultado.get("resumen_memoria_emergente", "")
        if emergente_resumen:
            existing = self.memoria.leer("analogia-emergente")
            self.memoria.escribir("analogia-emergente", f"{existing}\n\n### Formalización {r.nombre_texto}\n{emergente_resumen}")

        return resultado

    def _formatear_decisiones_para_prompt(self) -> str:
        decisiones = self.decisions.listar(tipo="lesson")[-10:]
        if not decisiones:
            return "No hay decisiones previas."
        partes = []
        for d in decisiones:
            partes.append(f"- {d['id']} ({d['tipo']}): {d['contenido'][:150]}")
        return "\n".join(partes)

    def _guardar_resultado(self, r: ResultadoPipeline):
        base = Path(__file__).resolve()
        for _ in range(4):
            base = base.parent
        output_dir = base / "data" / "pipeline_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = r.timestamp.strftime("%Y%m%d_%H%M%S")
        archivo = output_dir / f"{r.nombre_texto}_{timestamp}.json"
        contenido = json.dumps({
            "texto": r.nombre_texto,
            "timestamp": r.timestamp.isoformat(),
            "fase1": r.fase1,
            "fase2": r.fase2,
            "fase3": r.fase3,
            "fase4": r.fase4,
            "fase5": r.fase5,
            "fase6": r.fase6,
            "error": r.error,
        }, indent=2, default=str)
        try:
            archivo.write_text(contenido, encoding="utf-8")
        except OSError:
            tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8')
            tmp.write(contenido)
            tmp.close()
            subprocess.run(["powershell", "-Command",
                f"Copy-Item -LiteralPath '{tmp.name}' -Destination '{archivo}' -Force"],
                capture_output=True)
            Path(tmp.name).unlink(missing_ok=True)
        logger.info(f"Resultado guardado en: {archivo}")
