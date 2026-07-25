"""Exploración compacta del workspace para una única consulta al modelo."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__", "chroma_db", ".autocoder", "dist", "build"}
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".json",
    ".toml", ".yaml", ".yml", ".md", ".txt", ".sql", ".java", ".kt", ".go",
    ".rs", ".php", ".rb", ".cs", ".cpp", ".c", ".h", ".vue", ".svelte",
    ".gradle", ".properties", ".xml", ".bat", ".ps1",
}
IMPORTANT_NAMES = {
    "readme.md", "requirements.txt", "pyproject.toml", "package.json", "app.py",
    "main.py", "index.html", "cargo.toml", "go.mod", "build.gradle", "settings.gradle",
}


def _files(workspace: str, limit: int = 600) -> list[Path]:
    result = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in sorted(dirs) if d not in IGNORED_DIRS and not d.startswith(".")]
        for name in sorted(files):
            if name.startswith("."):
                continue
            result.append(Path(root) / name)
            if len(result) >= limit:
                return result
    return result


def explorar_workspace(workspace: str, max_chars: int = 60_000) -> tuple[str, str]:
    base = Path(workspace).resolve()
    files = _files(str(base))
    fingerprint = hashlib.sha256()
    relative = []
    for path in files:
        rel = path.relative_to(base).as_posix()
        try:
            stat = path.stat()
            fingerprint.update(f"{rel}:{stat.st_size}:{stat.st_mtime_ns}".encode())
        except OSError:
            continue
        relative.append((path, rel))

    tree = "\n".join(rel for _, rel in relative)
    remaining = max(0, max_chars - len(tree) - 1000)
    candidates = sorted(
        ((path, rel) for path, rel in relative
         if path.suffix.lower() in TEXT_EXTENSIONS or path.name.lower() in IMPORTANT_NAMES),
        key=lambda item: (item[0].name.lower() not in IMPORTANT_NAMES, len(item[0].parts), item[1]),
    )
    contents = []
    for path, rel in candidates:
        if remaining < 400:
            break
        try:
            if path.stat().st_size > 250_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        excerpt = text[: min(len(text), remaining, 12_000)]
        block = f"\n\n--- {rel} ---\n{excerpt}"
        contents.append(block)
        remaining -= len(block)

    snapshot = f"[ARCHIVOS DEL WORKSPACE]\n{tree or '(carpeta vacía)'}"
    if contents:
        snapshot += "\n\n[CONTENIDO DE ARCHIVOS RELEVANTES]" + "".join(contents)
    return snapshot, fingerprint.hexdigest()
