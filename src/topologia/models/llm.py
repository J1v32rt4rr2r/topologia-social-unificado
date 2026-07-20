from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from topologia.logger import logger

load_dotenv()


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
        self.client = OpenAI(api_key=api_key, base_url=base_url)

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
        for intento in range(max_retries):
            try:
                respuesta = self.client.chat.completions.create(**kwargs)
                return respuesta.choices[0].message.content or ""
            except Exception as e:
                if intento < max_retries - 1:
                    wait = 2 ** intento
                    logger.warning(f"LLM retry {intento + 1}/{max_retries} tras {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise

    def generar_json(
        self,
        prompt: str,
        temperatura: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict:
        texto = self.generar(prompt, temperatura, max_tokens, formato_json=True)
        texto_limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
        try:
            return json.loads(texto_limpio)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", texto_limpio, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

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
