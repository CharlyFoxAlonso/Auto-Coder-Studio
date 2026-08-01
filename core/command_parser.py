"""Catálogo estático y parser puro de slash commands.

No importa Streamlit, no lee disco, no ejecuta comandos, no llama al modelo.
Determinista: misma entrada produce mismo resultado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class NotACommand:
    raw: str


@dataclass(frozen=True)
class UnknownCommand:
    raw: str
    name: str
    args: str


@dataclass(frozen=True)
class KnownCommand:
    raw: str
    name: str
    args: str
    syntax: str
    description: str
    kind: Literal["normal", "redirect"]


ParsedCommand = NotACommand | UnknownCommand | KnownCommand


@dataclass(frozen=True)
class CommandDef:
    name: str
    aliases: tuple[str, ...]
    syntax: str
    description: str
    kind: Literal["normal", "redirect"]


CATALOG: tuple[CommandDef, ...] = (
    CommandDef(
        name="new",
        aliases=(),
        syntax="/new",
        description="nueva sesión",
        kind="normal",
    ),
    CommandDef(
        name="workspace",
        aliases=(),
        syntax="/workspace RUTA",
        description="seleccionar workspace",
        kind="normal",
    ),
    CommandDef(
        name="model",
        aliases=(),
        syntax="/model PROVEEDOR:MODELO",
        description="cambiar modelo",
        kind="normal",
    ),
    CommandDef(
        name="command",
        aliases=(),
        syntax="/command NOMBRE :: PROMPT",
        description="crear un comando reutilizable; usá `$ARGS`",
        kind="normal",
    ),
    CommandDef(
        name="skill",
        aliases=(),
        syntax="/skill NOMBRE :: DESCRIPCIÓN :: INSTRUCCIONES",
        description="crear una skill",
        kind="normal",
    ),
    CommandDef(
        name="function",
        aliases=(),
        syntax="/function NOMBRE :: DESCRIPCIÓN :: COMANDO",
        description="crear una función fija aprobable",
        kind="normal",
    ),
    CommandDef(
        name="stop",
        aliases=(),
        syntax="/stop",
        description="cancelar cualquier propuesta pendiente",
        kind="normal",
    ),
    CommandDef(
        name="clear",
        aliases=(),
        syntax="/clear",
        description="limpiar mensajes de esta sesión",
        kind="normal",
    ),
    CommandDef(
        name="help",
        aliases=("commands",),
        syntax="/help",
        description="mostrar esta ayuda",
        kind="normal",
    ),
    CommandDef(
        name="connect",
        aliases=(),
        syntax="",
        description="",
        kind="redirect",
    ),
    CommandDef(
        name="models",
        aliases=(),
        syntax="",
        description="",
        kind="redirect",
    ),
    CommandDef(
        name="sessions",
        aliases=(),
        syntax="",
        description="",
        kind="redirect",
    ),
)


def _build_index() -> dict[str, CommandDef]:
    index: dict[str, CommandDef] = {}
    for cmd in CATALOG:
        index[cmd.name] = cmd
        for alias in cmd.aliases:
            index[alias] = cmd
    return index


_INDEX: dict[str, CommandDef] = _build_index()


def parse(raw: str) -> ParsedCommand:
    """Identifica si `raw` es un slash command y devuelve el resultado estructurado.

    Reproduce exactamente la separación que hacía handle_command en app.py:
        if not raw.startswith("/"): return False, raw
        command, _, rest = raw[1:].partition(" ")
        command = command.lower()
    """
    if not raw.startswith("/"):
        return NotACommand(raw=raw)
    token, _, parts = raw[1:].partition(" ")
    token = token.lower()
    if token in _INDEX:
        cmd = _INDEX[token]
        return KnownCommand(
            raw=raw,
            name=cmd.name,
            args=parts,
            syntax=cmd.syntax,
            description=cmd.description,
            kind=cmd.kind,
        )
    return UnknownCommand(raw=raw, name=token, args=parts)


def generar_ayuda() -> str:
    """Reproduce el texto exacto de la antigua command_help() de app.py."""
    lines = ["Comandos disponibles:", ""]
    for cmd in CATALOG:
        if cmd.kind == "redirect":
            continue
        lines.append(f"- `{cmd.syntax}` — {cmd.description}")
    return "\n".join(lines) + "\n"
