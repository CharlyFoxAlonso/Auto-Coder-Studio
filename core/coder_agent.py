"""
Módulo de compatibilidad deprecated.

`forzar_json` fue movida a `core.parsers`.
Este módulo se conserva temporalmente para imports existentes.
"""

from core.parsers import forzar_json

__all__ = ["forzar_json"]
