"""Diálogo nativo de selección de carpetas para instalaciones locales."""
from __future__ import annotations

from pathlib import Path


def seleccionar_carpeta(initial_dir: str = "") -> tuple[str | None, str | None]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        selected = filedialog.askdirectory(
            parent=root,
            title="Seleccionar workspace para AutoCoder",
            initialdir=initial_dir if initial_dir and Path(initial_dir).is_dir() else str(Path.home()),
            mustexist=True,
        )
        root.destroy()
        return (str(Path(selected).resolve()), None) if selected else (None, None)
    except Exception as exc:
        return None, f"No se pudo abrir el selector nativo: {exc}"
