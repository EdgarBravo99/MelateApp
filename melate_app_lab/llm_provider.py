from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict


def get_llm_config() -> Dict[str, str]:
    """Carga configuracion LLM desde variables de entorno de forma segura."""
    return {
        "provider": os.environ.get("MELATE_LLM_PROVIDER", "disabled").lower(),
        "model": os.environ.get("MELATE_LLM_MODEL", "gpt-3.5-turbo"),
        "base_url": os.environ.get("MELATE_LLM_BASE_URL", ""),
        "api_key": os.environ.get("MELATE_LLM_API_KEY", ""),
        "timeout": os.environ.get("MELATE_LLM_TIMEOUT_SECONDS", "30"),
    }


def call_llm(prompt: str, system_prompt: str | None = None) -> str | None:
    """Invoca al LLM configurado usando urllib nativo para mantener cero dependencias."""
    config = get_llm_config()
    provider = config["provider"]

    if provider == "disabled" or provider == "local_stub":
        return None

    api_key = config["api_key"]
    base_url = config["base_url"].rstrip("/")
    model = config["model"]
    
    try:
        timeout = float(config["timeout"])
    except ValueError:
        timeout = 30.0

    if provider == "openai_compatible":
        if not base_url:
            base_url = "https://api.openai.com/v1"
        endpoint = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        return _make_request(endpoint, headers, payload, timeout)

    if provider == "local_http":
        if not base_url:
            base_url = "http://localhost:8080/completion"
        endpoint = base_url
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        # Generico para Llama.cpp / ollama raw
        full_prompt = ""
        if system_prompt:
            full_prompt += f"{system_prompt}\n\n"
        full_prompt += prompt
        
        payload = {
            "prompt": full_prompt,
            "temperature": 0.0,
            "n_predict": 1024,
            "stream": False
        }
        
        response_text = _make_request(endpoint, headers, payload, timeout)
        if response_text:
            try:
                data = json.loads(response_text)
                return data.get("content", data.get("response", response_text))
            except json.JSONDecodeError:
                return response_text
        return None

    # Fallback deterministico ante proveedor desconocido
    return None


def _make_request(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float) -> str | None:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = response.read().decode("utf-8")
            if "openai" in url or "chat/completions" in url:
                parsed = json.loads(result)
                if "choices" in parsed and len(parsed["choices"]) > 0:
                    return parsed["choices"][0]["message"]["content"]
            return result
    except (urllib.error.URLError, json.JSONDecodeError):
        # Fallback defensivo: errores de red no rompen la aplicacion
        return None
    except Exception:
        return None
