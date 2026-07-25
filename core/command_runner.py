"""Ejecución sin shell de validadores aprobados por el usuario."""
from __future__ import annotations

import os
import subprocess

ALLOWED = {"python", "python.exe", "pytest", "pytest.exe", "ruff", "ruff.exe",
           "node", "node.exe", "npm", "npm.cmd", "npx", "npx.cmd",
           "git", "git.exe", "gradlew", "gradlew.bat"}
DENIED_GIT = {"add", "commit", "push", "pull", "checkout", "switch", "reset", "clean", "rm", "mv"}


def validar_comando(argv: list[str]) -> tuple[bool, str]:
    if not argv or not all(isinstance(arg, str) and arg for arg in argv):
        return False, "El comando debe ser una lista de argumentos no vacíos."
    executable = os.path.basename(argv[0]).lower()
    if executable not in ALLOWED:
        return False, f"Ejecutable no permitido: {executable}"
    if executable in {"git", "git.exe"} and len(argv) > 1 and argv[1].lower() in DENIED_GIT:
        return False, "Ese subcomando de Git modifica estado y no está permitido."
    for arg in argv[1:]:
        if os.path.isabs(arg) or ".." in arg.replace("\\", "/").split("/"):
            return False, "Los argumentos no pueden salir del workspace."
    return True, ""


def ejecutar_comando(workspace: str, argv: list[str], timeout: int = 90) -> tuple[bool, str]:
    ok, error = validar_comando(argv)
    if not ok:
        return False, error
    try:
        result = subprocess.run(argv, cwd=workspace, shell=False, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        output = (result.stdout + ("\n" if result.stdout and result.stderr else "") + result.stderr)[-20_000:]
        return result.returncode == 0, f"exit={result.returncode}\n{output}".strip()
    except subprocess.TimeoutExpired:
        return False, f"El comando superó el timeout de {timeout}s."
    except OSError as exc:
        return False, f"No se pudo ejecutar: {exc}"
