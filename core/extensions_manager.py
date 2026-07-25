"""Comandos y skills declarativos; nunca ejecuta código arbitrario."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(".autocoder")
COMMANDS_FILE = ROOT / "commands.json"
FUNCTIONS_FILE = ROOT / "functions.json"
SKILLS_DIR = ROOT / "skills"


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "-", name.lower()).strip("-")[:48]


def cargar_comandos() -> dict[str, str]:
    try:
        data = json.loads(COMMANDS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def guardar_comando(name: str, prompt: str) -> str:
    name = _safe_name(name)
    if not name or not prompt.strip():
        raise ValueError("Nombre y prompt son obligatorios.")
    commands = cargar_comandos()
    commands[name] = prompt.strip()
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = COMMANDS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(commands, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, COMMANDS_FILE)
    return name


def cargar_funciones() -> dict[str, dict]:
    try:
        data = json.loads(FUNCTIONS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def guardar_funcion(name: str, description: str, argv: list[str]) -> str:
    name = _safe_name(name)
    if not name or not description.strip() or not argv:
        raise ValueError("Nombre, descripción y comando son obligatorios.")
    functions = cargar_funciones()
    functions[name] = {"description": description.strip(), "argv": argv}
    FUNCTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FUNCTIONS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(functions, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, FUNCTIONS_FILE)
    return name


def guardar_skill(name: str, description: str, instructions: str) -> str:
    name = _safe_name(name)
    if not name or not instructions.strip():
        raise ValueError("Nombre e instrucciones son obligatorios.")
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / f"{name}.md"
    path.write_text(f"# {name}\n\n{description.strip()}\n\n## Instrucciones\n\n{instructions.strip()}\n", encoding="utf-8")
    return name


def cargar_skills() -> list[dict]:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        skills.append({"name": path.stem, "content": text})
    return skills


def contexto_skills() -> str:
    skills = cargar_skills()
    if not skills:
        return ""
    return "\n\n".join(f"[SKILL {s['name']}]\n{s['content']}" for s in skills)
