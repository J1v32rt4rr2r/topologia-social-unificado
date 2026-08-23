from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

from topologia.logger import logger

load_dotenv()


_PARES_JSON = {"{": "}", "[": "]"}


def _extraer_json(texto: str) -> str:
    texto = texto.strip()
    bloque = re.search(r"```(?:json)?\s*(.*?)```", texto, re.DOTALL)
    if bloque:
        return bloque.group(1).strip()
    primer_json = re.search(r"[\[\{]", texto)
    if primer_json:
        return texto[primer_json.start():].strip()
    return texto


def _recortar_balanceado(texto: str, apertura: str) -> str | None:
    pila = [_PARES_JSON[apertura]]
    en_string = False
    escape = False
    for i, ch in enumerate(texto[1:], start=1):
        if en_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                en_string = False
            continue
        if ch == '"':
            en_string = True
        elif ch == "{":
            pila.append("}")
        elif ch == "[":
            pila.append("]")
        elif ch in "}]":
            if not pila or ch != pila[-1]:
                return None
            pila.pop()
            if not pila:
                return texto[:i + 1]
    return None


def _parsear_json(texto: str) -> dict | list:
    contenido = _extraer_json(texto)
    try:
        return json.loads(contenido)
    except json.JSONDecodeError:
        pass
    decodificador = json.JSONDecoder()
    try:
        valor, _ = decodificador.raw_decode(contenido)
        return valor
    except json.JSONDecodeError:
        pass
    for apertura in _PARES_JSON:
        inicio = contenido.find(apertura)
        if inicio == -1:
            continue
        fragmento = _recortar_balanceado(contenido[inicio:], apertura)
        if fragmento is None:
            continue
        try:
            return json.loads(fragmento)
        except json.JSONDecodeError:
            pass
    raise ValueError("respuesta del LLM no contiene JSON parseable")


class LLMClient:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._init_client()
            self._initialized = True

    def _init_client(self):
        api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.modelo = os.getenv("LLM_MODELO", "deepseek-chat")
        self.es_ollama = "11434" in base_url or "ollama" in base_url.lower()
        # Timeout explícito: un proveedor lento no debe congelar el ciclo
        # (los reintentos se gestionan en generar(); el SDK no reintenta).
        timeout = float(os.getenv("LLM_TIMEOUT", "300"))
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
        )

    def generar(
        self,
        prompt: str,
        temperatura: float = 0.2,
        max_tokens: int = 2048,
        formato_json: bool = False,
        max_retries: int = 3,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperatura,
            "max_tokens": max_tokens,
        }
        if formato_json:
            kwargs["response_format"] = {"type": "json_object"}

        # Modelos de razonamiento (p. ej. deepseek-v4-flash) gastan max_tokens en
        # reasoning_content y pueden devolver content vacío. Deshabilitar el
        # razonamiento cuando el proveedor lo soporte (DeepSeek); Ollama usa su
        # propio flag 'think' y rechaza/ignora extra_body, por lo que se omite.
        payload = dict(kwargs)
        if not self.es_ollama and os.getenv("LLM_THINKING_DISABLED", "1") == "1":
            payload["extra_body"] = {"thinking": {"type": "disabled"}}

        for intento in range(max_retries):
            try:
                respuesta = self.client.chat.completions.create(**payload)
                contenido = respuesta.choices[0].message.content or ""
                if not contenido.strip():
                    raise ValueError("respuesta vacía del LLM")
                return contenido
            except APIStatusError as e:
                if e.status_code == 400 and "extra_body" in payload:
                    logger.warning("LLM: proveedor rechazó 'thinking' (HTTP 400), reintentando sin el parámetro")
                    del payload["extra_body"]
                    continue
                if intento < max_retries - 1:
                    wait = 2 ** intento
                    logger.warning(f"LLM retry {intento + 1}/{max_retries} tras {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                if intento < max_retries - 1:
                    wait = 2 ** intento
                    logger.warning(f"LLM retry {intento + 1}/{max_retries} tras {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError("LLM falló tras reintentos")

    def generar_json(
        self,
        prompt: str,
        temperatura: float = 0.2,
        max_tokens: int = 2048,
        max_parse_intentos: int = 3,
    ) -> dict | list:
        ultimo_error: Exception | None = None
        for intento in range(max_parse_intentos):
            try:
                texto = self.generar(prompt, temperatura, max_tokens, formato_json=True)
                valor = _parsear_json(texto)
                if not isinstance(valor, (dict, list)):
                    raise ValueError(
                        f"JSON no es objeto ni lista: {type(valor).__name__}"
                    )
                return valor
            except (json.JSONDecodeError, ValueError) as e:
                ultimo_error = e
                if intento < max_parse_intentos - 1:
                    logger.warning(
                        f"JSON no parseable (intento {intento + 1}/{max_parse_intentos}): {e}"
                    )
        raise ultimo_error

    def generar_numero(
        self,
        prompt: str,
        temperatura: float = 0.2,
    ) -> tuple[float, str]:
        texto = self.generar(prompt, temperatura, max_tokens=512)
        num_match = re.search(r"N[UÚ]MERO:\s*([\d.]+)", texto)
        just_match = re.search(r"JUSTIFICACI[OÓ]N:\s*(.+)", texto)
        numero = float(num_match.group(1)) if num_match else 5.0
        justificacion = just_match.group(1).strip() if just_match else texto.strip()[:200]
        return (numero, justificacion)


def test_llm() -> str:
    client = LLMClient()
    try:
        texto = client.generar("Responde solo: OK", temperatura=0.1, max_tokens=10)
        return f"LLM OK: {texto.strip()}"
    except Exception as e:
        return f"LLM ERROR: {e}"
