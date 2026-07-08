"""
core/security.py
"""
import os
import re

EXTENSIONES_PROHIBIDAS = {'.exe', '.bat', '.sh', '.dll', '.so', '.cmd'}

def validar_ruta_segura(ruta_base, ruta_archivo):
    base_real = os.path.realpath(ruta_base)
    archivo_real = os.path.realpath(os.path.join(base_real, ruta_archivo))
    if not archivo_real.startswith(base_real):
        return False, "Acceso denegado: Ruta fuera del directorio permitido."
    return True, ""

def es_extension_segura(nombre_archivo):
    _, ext = os.path.splitext(nombre_archivo)
    return ext.lower() not in EXTENSIONES_PROHIBIDAS

def sanitizar_nombre_archivo(nombre):
    """Elimina caracteres peligrosos del nombre del archivo."""
    # Permite solo letras, números, guiones, guiones bajos y puntos
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', nombre)