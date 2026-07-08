"""
core/file_manager.py
Gestiona la lectura, escritura y exploración segura de archivos.
Incluye validaciones anti-path-traversal y límites de seguridad.
"""
import os
import difflib
from core.security import validar_ruta_segura, es_extension_segura

def listar_archivos(ruta_base):
    """Lista todos los archivos y carpetas dentro de ruta_base.

    Devuelve una tupla (estructura_str, error_str):
      - En éxito: (string_con_arbol, "")
      - En error:  ("", mensaje_de_error)
    """
    ok, msg = validar_ruta_segura(ruta_base, ".")
    if not ok:
        return "", msg

    estructura = []
    try:
        for root, dirs, files in os.walk(ruta_base):
            # Ignorar carpetas ocultas y virtuales
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            nivel = root.replace(ruta_base, '').count(os.sep)
            indent = '  ' * nivel

            # Agregar carpetas
            for d in sorted(dirs):
                estructura.append(f"{indent}📁 {d}/")

            # Agregar archivos
            for f in sorted(files):
                if not f.startswith('.'):
                    estructura.append(f"{indent} {f}")

        return "\n".join(estructura), ""
    except Exception as e:
        return "", f"Error listando directorio: {str(e)}"

def leer_archivo(ruta_base, ruta_relativa):
    """Lee el contenido completo de un archivo."""
    ok, msg = validar_ruta_segura(ruta_base, ruta_relativa)
    if not ok:
        return None, msg
    
    ruta_completa = os.path.join(ruta_base, ruta_relativa)
    if not os.path.exists(ruta_completa):
        return None, f"Archivo no encontrado: {ruta_relativa}"
        
    try:
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            return f.read(), ""
    except UnicodeDecodeError:
        return None, "No se pudo leer: El archivo parece ser binario."
    except Exception as e:
        return None, f"Error leyendo archivo: {str(e)}"

def escribir_archivo(ruta_base, ruta_relativa, contenido):
    """Escribe o sobreescribe un archivo tras validación de seguridad."""
    ok, msg = validar_ruta_segura(ruta_base, ruta_relativa)
    if not ok:
        return False, msg
        
    if not es_extension_segura(ruta_relativa):
        return False, f"Extensión prohibida por seguridad: {os.path.splitext(ruta_relativa)[1]}"
        
    ruta_completa = os.path.join(ruta_base, ruta_relativa)
    dir_padre = os.path.dirname(ruta_completa)
    if dir_padre:
        os.makedirs(dir_padre, exist_ok=True)
    
    try:
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return True, f"✅ Archivo actualizado: {ruta_relativa}"
    except Exception as e:
        return False, f"❌ Error escribiendo: {str(e)}"

def generar_diff(ruta_base, ruta_relativa, nuevo_contenido):
    """Genera un diff visual para que el usuario apruebe cambios."""
    contenido_actual, _ = leer_archivo(ruta_base, ruta_relativa)
    if contenido_actual is None:
        return "--- Archivo nuevo (no existía previamente) ---\n" + nuevo_contenido
        
    diff = difflib.unified_diff(
        contenido_actual.splitlines(keepends=True),
        nuevo_contenido.splitlines(keepends=True),
        fromfile=f"a/{ruta_relativa}",
        tofile=f"b/{ruta_relativa}",
        lineterm=''
    )
    return "\n".join(diff)

def borrar_archivo(ruta_base, ruta_relativa):
    """Borra un archivo de forma segura."""
    ok, msg = validar_ruta_segura(ruta_base, ruta_relativa)
    if not ok:
        return False, msg
    
    ruta_completa = os.path.join(ruta_base, ruta_relativa)
    try:
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
            return True, f"✅ Archivo eliminado: {ruta_relativa}"
        else:
            return False, f"Error: El archivo {ruta_relativa} no existe."
    except Exception as e:
        return False, f"Error al borrar archivo: {str(e)}"