"""Utilidades para extraer acciones JSON de respuestas de modelos."""

import json

__all__ = ["forzar_json"]


def forzar_json(respuesta):
    """Intenta extraer y validar JSON de la respuesta del modelo.

    Es tolerante con code fences ```json ... ``` y devuelve None si no
    encuentra un JSON válido con la estructura esperada.
    """
    if not respuesta:
        return None

    texto = respuesta.strip()

    # Quitar code fences si el modelo los añadió
    if texto.startswith("```"):
        # ```json\n ... \n```
        lineas = texto.splitlines()
        if lineas and lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].strip().startswith("```"):
            lineas = lineas[:-1]
        texto = "\n".join(lineas)

    # Buscar el primer '{' y el último '}' balanceado para no cortar
    # el contenido del archivo (que puede contener llaves).
    start = texto.find('{')
    if start == -1:
        return None

    profundidad = 0
    fin = -1
    en_string = False
    escape = False
    for i in range(start, len(texto)):
        c = texto[i]
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c == '"':
            en_string = not en_string
            continue
        if en_string:
            continue
        if c == '{':
            profundidad += 1
        elif c == '}':
            profundidad -= 1
            if profundidad == 0:
                fin = i
                break

    if fin == -1:
        return None

    try:
        data = json.loads(texto[start:fin + 1])
        # Validar que tenga las claves necesarias
        if (("herramienta" in data and "argumentos" in data)
                or isinstance(data.get("acciones"), list)):
            return data
        return None
    except json.JSONDecodeError:
        return None
