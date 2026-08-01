"""Módulo interno que encapsula toda la persistencia física de sesiones.

Este módulo contiene únicamente operaciones de I/O y (des)serialización JSON.
No incluye lógica de dominio ni decisiones sobre cuándo guardar.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# Directorio base de la aplicación (igual que antes)
DATA_DIR = Path(".autocoder")
SESSIONS_DIR = DATA_DIR / "sessions"


def _ensure() -> None:
    """Asegura que el directorio de sesiones exista.

    Se mantiene idéntico al comportamiento anterior de ``session_manager._ensure``.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    """Construye la ruta del archivo de una sesión a partir de su ID.

    Se conserva la sanitización de caracteres alfanuméricos, guiones y guiones bajos.
    """
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return SESSIONS_DIR / f"{safe_id}.json"


def save_session(data: dict) -> None:
    """Escribe la sesión en disco de forma atómica.

    Mantiene exactamente el mismo formato de JSON que la versión original:
    ``ensure_ascii=False``, ``indent=2`` y ``utf-8``.
    """
    _ensure()
    target = _session_path(data["id"])  # el dict siempre contiene "id"
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


def load_session(session_id: str) -> dict | None:
    """Carga una sesión desde disco.

    Devuelve ``None`` si el archivo no existe o contiene JSON inválido, igual que
    la implementación original.
    """
    try:
        with _session_path(session_id).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def list_sessions() -> list[dict]:
    """Lista todas las sesiones almacenadas.

    El formato de los elementos devueltos coincide con la versión anterior.
    """
    _ensure()
    sessions: list[dict] = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            sessions.append({
                k: data.get(k)
                for k in (
                    "id",
                    "title",
                    "workspace",
                    "provider_id",
                    "model",
                    "input_tokens",
                    "output_tokens",
                    "updated_at",
                )
            })
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(sessions, key=lambda item: item.get("updated_at") or "", reverse=True)


def delete_session(session_id: str) -> bool:
    """Elimina la sesión del disco.

    Retorna ``True`` incluso si el archivo no existía (comportamiento original).
    """
    try:
        _session_path(session_id).unlink(missing_ok=True)
        return True
    except OSError:
        return False
