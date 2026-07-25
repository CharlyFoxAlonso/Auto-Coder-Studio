"""Persistencia local y atómica de sesiones de chat."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(".autocoder")
SESSIONS_DIR = DATA_DIR / "sessions"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _path(session_id: str) -> Path:
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return SESSIONS_DIR / f"{safe_id}.json"


def nueva_sesion(workspace: str = "", provider_id: str = "ollama", model: str = "") -> dict:
    session_id = uuid.uuid4().hex
    now = _now()
    data = {
        "id": session_id,
        "title": "Nueva sesión",
        "workspace": workspace,
        "provider_id": provider_id,
        "model": model,
        "messages": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "created_at": now,
        "updated_at": now,
    }
    guardar_sesion(data)
    return data


def guardar_sesion(data: dict) -> None:
    _ensure()
    data["updated_at"] = _now()
    target = _path(data["id"])
    fd, tmp_name = tempfile.mkstemp(prefix="session-", suffix=".json", dir=SESSIONS_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def cargar_sesion(session_id: str) -> dict | None:
    try:
        with _path(session_id).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def listar_sesiones() -> list[dict]:
    _ensure()
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            sessions.append({k: data.get(k) for k in (
                "id", "title", "workspace", "provider_id", "model",
                "input_tokens", "output_tokens", "updated_at"
            )})
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(sessions, key=lambda item: item.get("updated_at") or "", reverse=True)


def borrar_sesion(session_id: str) -> bool:
    try:
        _path(session_id).unlink(missing_ok=True)
        return True
    except OSError:
        return False


def agregar_mensaje(data: dict, role: str, content: str, **extra) -> None:
    message = {"role": role, "content": content, "created_at": _now(), **extra}
    data.setdefault("messages", []).append(message)
    if data.get("title") == "Nueva sesión" and role == "user" and not content.startswith("/"):
        data["title"] = content.strip().replace("\n", " ")[:52] or "Nueva sesión"


def limpiar_mensajes_del_loop(data: dict) -> int:
    """Retira rastros técnicos producidos por el antiguo motor iterativo."""
    cleaned = []
    removed = 0
    tool_prefixes = ("list_files", "read_file", "write_file", "delete_file", "run_command")
    for message in data.get("messages", []):
        role = message.get("role")
        content = message.get("content", "").strip()
        technical = role == "tool"
        technical = technical or (
            role == "assistant" and (
                content.startswith("[Respuesta inválida")
                or content.startswith("[Finalización rechazada")
                or content.startswith("TERMINADO:")
                or any(content.startswith(f"`{name}`") for name in tool_prefixes)
            )
        )
        technical = technical or (role == "user" and content.lower() in {"stop", "/stop"})
        if technical:
            removed += 1
        else:
            cleaned.append(message)
    data["messages"] = cleaned
    return removed
