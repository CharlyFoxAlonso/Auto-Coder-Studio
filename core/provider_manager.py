"""Proveedores LLM configurables con métricas de tokens normalizadas."""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

CONFIG_FILE = Path(".autocoder/providers.json")

DEFAULTS = [
    {
        "id": "ollama",
        "name": "Ollama local",
        "kind": "ollama",
        "base_url": os.getenv("OLLAMA_CHAT_URL", os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")),
        "models": [os.getenv("MODELO_CODER", "qwen2.5-coder:7b")],
        "api_key_env": "",
    }
]


def _atomic_write(data: object) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_FILE)


def cargar_proveedores() -> list[dict]:
    if not CONFIG_FILE.exists():
        return [dict(item) for item in DEFAULTS]
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) and data else [dict(item) for item in DEFAULTS]
    except (OSError, json.JSONDecodeError):
        return [dict(item) for item in DEFAULTS]


def guardar_proveedor(provider: dict) -> None:
    providers = cargar_proveedores()
    providers = [p for p in providers if p.get("id") != provider.get("id")]
    providers.append(provider)
    _atomic_write(providers)


def obtener_proveedor(provider_id: str) -> dict | None:
    return next((p for p in cargar_proveedores() if p.get("id") == provider_id), None)


def descubrir_modelos(provider: dict, secrets: dict | None = None, timeout: int = 10) -> list[str]:
    """Consulta modelos cuando el proveedor expone un endpoint compatible."""
    kind = provider.get("kind", "openai")
    base_url = provider.get("base_url", "").rstrip("/")
    if kind == "ollama":
        root = base_url.split("/api/")[0]
        response = requests.get(f"{root}/api/tags", timeout=timeout)
        response.raise_for_status()
        return sorted(m["name"] for m in response.json().get("models", []) if m.get("name"))
    if kind == "openai":
        root = base_url.removesuffix("/chat/completions")
        response = requests.get(f"{root}/models", timeout=timeout,
                                headers={"Authorization": f"Bearer {_key(provider, secrets)}"})
        response.raise_for_status()
        return sorted(m["id"] for m in response.json().get("data", []) if m.get("id"))
    return provider.get("models", [])


def sincronizar_modelos(provider: dict, secrets: dict | None = None,
                         timeout: int = 10) -> tuple[list[str], bool]:
    """Descubre y persiste una lista nueva sin cambiar el modelo activo."""
    discovered = list(dict.fromkeys(descubrir_modelos(provider, secrets, timeout)))
    if not discovered:
        return [], False
    changed = discovered != provider.get("models", [])
    if changed:
        guardar_proveedor({**provider, "models": discovered})
    return discovered, changed


def _estimate(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _key(provider: dict, secrets: dict | None) -> str:
    if secrets and secrets.get(provider["id"]):
        return secrets[provider["id"]]
    env_name = provider.get("api_key_env", "")
    return os.getenv(env_name, "") if env_name else ""


def chat(provider: dict, model: str, messages: list[dict], secrets: dict | None = None,
         timeout: int = 300) -> tuple[str, dict]:
    kind = provider.get("kind", "openai")
    base_url = provider.get("base_url", "").rstrip("/")
    api_key = _key(provider, secrets)
    normalized = [{"role": m["role"], "content": m.get("content", "")}
                  for m in messages if m.get("role") in {"system", "user", "assistant"}]

    if kind == "ollama":
        url = base_url if base_url.endswith("/api/chat") else f"{base_url}/api/chat"
        response = requests.post(
            url,
            json={"model": model, "messages": normalized, "stream": False,
                  "options": {"temperature": 0.1, "num_ctx": 32768}},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload["message"]["content"].strip()
        usage = {"input": payload.get("prompt_eval_count", 0), "output": payload.get("eval_count", 0)}
    elif kind == "anthropic":
        system = "\n\n".join(m["content"] for m in normalized if m["role"] == "system")
        body = {"model": model, "max_tokens": 8192,
                "messages": [m for m in normalized if m["role"] != "system"]}
        if system:
            body["system"] = system
        response = requests.post(
            base_url or "https://api.anthropic.com/v1/messages", json=body, timeout=timeout,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        )
        response.raise_for_status()
        payload = response.json()
        text = "".join(block.get("text", "") for block in payload.get("content", []))
        raw = payload.get("usage", {})
        usage = {"input": raw.get("input_tokens", 0), "output": raw.get("output_tokens", 0)}
    else:
        url = base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        response = requests.post(url, json={"model": model, "messages": normalized}, timeout=timeout,
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        response.raise_for_status()
        payload = response.json()
        text = payload["choices"][0]["message"]["content"].strip()
        raw = payload.get("usage", {})
        usage = {"input": raw.get("prompt_tokens", 0), "output": raw.get("completion_tokens", 0)}

    usage["input"] = usage["input"] or sum(_estimate(m["content"]) for m in normalized)
    usage["output"] = usage["output"] or _estimate(text)
    return text, usage
