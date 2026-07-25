"""
core/security.py
"""
import os
import re

EXTENSIONES_PROHIBIDAS = {'.exe', '.bat', '.sh', '.dll', '.so', '.cmd'}

def validar_ruta_segura(ruta_base, ruta_archivo):
    if not ruta_base or not ruta_archivo:
        return False, "La ruta base y la ruta del archivo son obligatorias."
    base_real = os.path.normcase(os.path.realpath(os.path.abspath(ruta_base)))
    if os.path.isabs(ruta_archivo):
        return False, "Acceso denegado: Se requieren rutas relativas."
    archivo_real = os.path.normcase(
        os.path.realpath(os.path.abspath(os.path.join(base_real, ruta_archivo)))
    )
    try:
        dentro = os.path.commonpath([base_real, archivo_real]) == base_real
    except ValueError:
        dentro = False
    if not dentro:
        return False, "Acceso denegado: Ruta fuera del directorio permitido."
    return True, ""

def es_extension_segura(nombre_archivo):
    _, ext = os.path.splitext(nombre_archivo)
    return ext.lower() not in EXTENSIONES_PROHIBIDAS

def sanitizar_nombre_archivo(nombre):
    """Elimina caracteres peligrosos del nombre del archivo."""
    # Permite solo letras, números, guiones, guiones bajos y puntos
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', nombre)
