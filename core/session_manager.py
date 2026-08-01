"""Persistencia local y atómica de sesiones de chat (delegada a core.session_storage)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

# Importar la capa de almacenamiento de sesiones.
from core.session_storage import (
    _ensure,
    _session_path,
    save_session,
    load_session,
    list_sessions,
    delete_session,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()



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
    # Delegamos la persistencia a core.session_storage
    data["updated_at"] = _now()
    save_session(data)


def cargar_sesion(session_id: str) -> dict | None:
    return load_session(session_id)


def listar_sesiones() -> list[dict]:
    return list_sessions()


def borrar_sesion(session_id: str) -> bool:
    return delete_session(session_id)


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
