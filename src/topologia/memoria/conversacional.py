"""Memoria conversacional del Redactor.

Replica la semántica de ConversationSummaryBufferMemory de LangChain:
un buffer de mensajes crudos acotado por max_token_limit; al excederlo,
los mensajes más antiguos se pliegan en un resumen rodante generado por LLM.

Además implementa archivado mensual: cada 30 días el resumen rodante se sella
en un bloque de "memoria permanente" (se sigue enviando como contexto, pero el
resumen rodante se reinicia), de modo que el costo y la calidad de contexto se
estabilizan indefinidamente.

La clase oficial de langchain 1.x fue removida (langchain.memory no existe en
1.3+), por lo que la implementación es propia, usando tiktoken para el conteo de
tokens y LLMClient (el cliente del proyecto, con thinking deshabilitado) para
los resúmenes.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from topologia.logger import logger
from topologia.models.schemas import (
    EstadoCultural,
    Especulacion,
    InformeDiario,
    OperacionCinetica,
)
from topologia.paths import get_memoria_dir

#: Cantidad máxima de bloques permanentes enviados como contexto
MAX_BLOQUES_PERMANENTES = 6

#: Tope del resumen rodante (el prompt pide ~400 tokens; se valida el largo)
MAX_CARACTERES_RESUMEN = 1800

#: Si el buffer supera max_token_limit * este factor, se descartan los más
#: antiguos sin resumir (garantía de acotamiento incluso si el LLM falla)
FACTOR_TOLERANCIA = 3

PROMPT_RESUMEN = """Eres el sistema de memoria del Redactor de un sistema de monitoreo cultural. Produce UN resumen cronológico compacto que consolide la información acumulada.

REGLAS:
- Conserva solo hitos: cambios estructurales de delta y las matrices (M_m, M_l, M_s), el riesgo R si varió, operaciones recurrentes, tensiones latentes, especulaciones relevantes y su verificación, decisiones del Árbitro y datos de cobertura.
- Omite detalles repetitivos, listas extensas y ruido.
- Extensión máxima: ~400 tokens (aproximadamente 1200-1600 caracteres).
- Escribe en español, en párrafos breves y cronológicos.

RESUMEN ANTERIOR:
{resumen_anterior}

NUEVOS FRAGMENTOS:
{fragmentos}

NUEVO RESUMEN:"""


def _estimar_tokens(texto: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(texto))
    except Exception:
        return max(1, len(texto) // 3)


class MemoriaRedactor:
    def __init__(
        self,
        sociedad: str = "Chile",
        ruta: str | Path | None = None,
        max_token_limit: int = 2000,
        llm: Callable[..., str] | None = None,
    ):
        self.sociedad = sociedad
        self.max_token_limit = max_token_limit
        if ruta is None:
            ruta = get_memoria_dir() / "conversacional" / f"{sociedad}_redactor.json"
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.buffer: list[dict[str, str]] = []
        self.resumen_rodante = ""
        self.memoria_permanente: list[dict[str, str]] = []
        self.primer_dia_resumen: str | None = None
        self.ultima_fecha: str | None = None
        if llm is None:
            from topologia.models.llm import LLMClient

            self._llm = LLMClient().generar
        else:
            self._llm = llm
        self._cargar()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def _cargar(self) -> None:
        if not self.ruta.exists():
            return
        try:
            data = json.loads(self.ruta.read_text(encoding="utf-8"))
            self.buffer = data.get("buffer", [])
            self.resumen_rodante = data.get("resumen_rodante", "")
            self.memoria_permanente = data.get("memoria_permanente", [])
            self.primer_dia_resumen = data.get("primer_dia_resumen")
            self.ultima_fecha = data.get("ultima_fecha")
        except Exception as e:
            logger.warning(f"MemoriaRedactor: no se pudo cargar {self.ruta}: {e}")

    def _guardar(self) -> None:
        data = {
            "sociedad": self.sociedad,
            "buffer": self.buffer,
            "resumen_rodante": self.resumen_rodante,
            "memoria_permanente": self.memoria_permanente,
            "primer_dia_resumen": self.primer_dia_resumen,
            "ultima_fecha": self.ultima_fecha,
        }
        self.ruta.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _tokens_buffer(self) -> int:
        return _estimar_tokens("\n\n".join(m["content"] for m in self.buffer))

    @staticmethod
    def _texto_informe(informe: InformeDiario) -> str:
        partes = []
        for campo in ("resumen_ejecutivo", "panorama", "dinamicas", "especulaciones_y_estudios", "mirada_adelante"):
            val = getattr(informe, campo, "") or ""
            if val:
                partes.append(val.strip())
        return "\n".join(partes)

    @staticmethod
    def _parsear_fecha(valor: str | date) -> date:
        if isinstance(valor, date):
            return valor
        return date.fromisoformat(valor)

    @staticmethod
    def _fecha_de_mensaje(mensaje: dict[str, str]) -> str | None:
        """Extrae la fecha del contexto human ('Día YYYY-MM-DD: ...')."""
        if mensaje.get("role") != "human":
            return None
        match = re.match(r"Día (\d{4}-\d{2}-\d{2})", mensaje.get("content", ""))
        return match.group(1) if match else None

    # ------------------------------------------------------------------
    # Resumen rodante
    # ------------------------------------------------------------------
    def _resumir(self, fragmentos: str) -> str | None:
        """Piega el resumen anterior + fragmentos nuevos en un resumen nuevo."""
        if not fragmentos.strip():
            return None
        prompt = PROMPT_RESUMEN.format(
            resumen_anterior=self.resumen_rodante or "(sin resumen previo)",
            fragmentos=fragmentos,
        )
        try:
            texto = self._llm(prompt, temperatura=0.2, max_tokens=600)
        except Exception as e:
            logger.warning(f"MemoriaRedactor: falló el resumen LLM: {e}")
            return None
        texto = (texto or "").strip()
        if len(texto) > MAX_CARACTERES_RESUMEN:
            texto = texto[:MAX_CARACTERES_RESUMEN]
        return texto

    def _pruning(self) -> None:
        """Mueve los mensajes más antiguos del buffer al resumen rodante."""
        tokens = self._tokens_buffer()
        if tokens <= self.max_token_limit:
            return
        evictados: list[dict[str, str]] = []
        while self.buffer and self._tokens_buffer() > self.max_token_limit:
            evictados.append(self.buffer.pop(0))
        if not evictados:
            return
        fragmentos = "\n\n".join(f"[{m['role']}] {m['content']}" for m in evictados)
        nuevo_resumen = self._resumir(fragmentos)
        if nuevo_resumen is None:
            # El LLM falló: devolvemos los mensajes al buffer para no perder
            # información; si el buffer crece sin límite, se recorta igual.
            self.buffer = evictados + self.buffer
            if self._tokens_buffer() > self.max_token_limit * FACTOR_TOLERANCIA:
                exceso = self._tokens_buffer() - self.max_token_limit * FACTOR_TOLERANCIA
                sobrante = []
                while self.buffer and exceso > 0 and len(self.buffer) > 1:
                    m = self.buffer.pop(0)
                    exceso -= _estimar_tokens(m["content"])
                    sobrante.append(m["role"])
                logger.warning(
                    f"MemoriaRedactor: buffer sobre tolerancia, descartados "
                    f"{len(sobrante)} mensajes antiguos sin resumir"
                )
            return
        self.resumen_rodante = nuevo_resumen
        if self.primer_dia_resumen is None:
            self.primer_dia_resumen = next(
                (fecha for m in evictados if (fecha := self._fecha_de_mensaje(m))),
                self.ultima_fecha,
            )
        logger.info(
            f"MemoriaRedactor: resumen rodante actualizado ({len(evictados)} "
            f"mensajes plegados, buffer {self._tokens_buffer()} tokens)"
        )

    def _archivar_si_corresponde(self, fecha: date) -> None:
        """Cada 30 días, sella el resumen rodante en la memoria permanente."""
        if not self.resumen_rodante or not self.primer_dia_resumen:
            return
        dias = (fecha - self._parsear_fecha(self.primer_dia_resumen)).days
        if dias < 30:
            return
        self.memoria_permanente.append({
            "desde": self.primer_dia_resumen,
            "hasta": fecha.isoformat(),
            "resumen": self.resumen_rodante,
        })
        self.resumen_rodante = ""
        self.primer_dia_resumen = None
        logger.info(
            f"MemoriaRedactor: archivado mensual sellado "
            f"({len(self.memoria_permanente)} bloques permanentes)"
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def registrar_dia(
        self,
        fecha: str | date,
        estado: EstadoCultural | None = None,
        operaciones: list[OperacionCinetica] | None = None,
        especulaciones: list[Especulacion] | None = None,
        informe: InformeDiario | None = None,
        cobertura: str = "",
    ) -> dict:
        """Registra el intercambio de un día: contexto breve (human) + informe (ai)."""
        f = self._parsear_fecha(fecha)
        contexto = f"Día {f.isoformat()}: "
        if estado:
            contexto += (
                f"δ={estado.delta_promedio:.1f}°, M=({estado.M_m:.1f}, "
                f"{estado.M_l:.1f}, {estado.M_s:.1f})"
            )
            if estado.nodos_fragiles:
                contexto += f", frágiles: {', '.join(estado.nodos_fragiles)}"
        if operaciones:
            contexto += f"; operaciones: {', '.join(o.codigo for o in operaciones)}"
        if especulaciones:
            contexto += f"; {len(especulaciones)} especulaciones"
        if cobertura:
            contexto += f"; cobertura: {cobertura}"
        informe_texto = self._texto_informe(informe) if informe else ""
        self.buffer.append({"role": "human", "content": contexto})
        if informe_texto:
            self.buffer.append({"role": "ai", "content": informe_texto})
        self.ultima_fecha = f.isoformat()
        self._pruning()
        self._archivar_si_corresponde(f)
        self._guardar()
        return self.metricas()

    def contexto(self) -> dict:
        """Contexto para el prompt del Redactor (informe_anterior + métricas)."""
        partes: list[str] = []
        if self.memoria_permanente:
            bloques = self.memoria_permanente[-MAX_BLOQUES_PERMANENTES:]
            texto_bloques = "\n\n".join(
                f"[{b['desde']} → {b['hasta']}] {b['resumen']}" for b in bloques
            )
            partes.append(f"=== MEMORIA DE LARGO PLAZO (períodos previos) ===\n{texto_bloques}")
        if self.resumen_rodante:
            desde = self.primer_dia_resumen or "?"
            partes.append(f"=== RESUMEN RODANTE (desde {desde}) ===\n{self.resumen_rodante}")
        if self.buffer:
            crudo = "\n\n".join(
                f"[{m['role']}] {m['content']}" for m in self.buffer
            )
            partes.append(f"=== ÚLTIMOS DÍAS (texto íntegro) ===\n{crudo}")
        return {
            "informe_anterior": "\n\n".join(partes),
            "metricas": self.metricas(),
        }

    def metricas(self) -> dict:
        crudo = "\n\n".join(m["content"] for m in self.buffer)
        return {
            "buffer_tokens": _estimar_tokens(crudo),
            "buffer_mensajes": len(self.buffer),
            "resumen_rodante_tokens": _estimar_tokens(self.resumen_rodante),
            "permanente_tokens": _estimar_tokens(
                "\n\n".join(b["resumen"] for b in self.memoria_permanente)
            ),
            "bloques_permanentes": len(self.memoria_permanente),
            "primer_dia_resumen": self.primer_dia_resumen,
            "ultima_fecha": self.ultima_fecha,
        }
