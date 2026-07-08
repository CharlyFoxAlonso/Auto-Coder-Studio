"""
core/coder_agent.py - Versión Optimizada para Loop
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODELO_CODER = os.getenv("MODELO_CODER", "qwen2.5-coder:7b")

PROMPT_SISTEMA = """Eres un agente programador AUTÓNOMO. Creás archivos REALES en el sistema de archivos y tenés acceso a una biblioteca de conocimientos local (RAG).

FORMATO OBLIGATORIO - Respondé EXACTAMENTE en JSON puro, una sola línea, sin markdown ni texto extra:

Para CREAR/MODIFICAR archivos:
{"herramienta": "write_file", "argumentos": {"ruta": "archivo.ext", "contenido": "contenido completo"}, "pensamiento": "razón breve"}

Para LISTAR: {"herramienta": "list_files", "argumentos": {}, "pensamiento": "viendo"}
Para LEER: {"herramienta": "read_file", "argumentos": {"ruta": "archivo.ext"}, "pensamiento": "leyendo"}
Para BUSCAR EN LA BIBLIOTECA: {"herramienta": "buscar_conocimiento", "argumentos": {"query": "lo que buscás", "cajon": "opcional", "subcajon": "opcional"}, "pensamiento": "consultando documentación"}

Cuando TERMINES:
TERMINADO: [instrucciones de uso]

EJEMPLO COMPLETO DE CONVERSACIÓN:
Usuario: Creá hola.html con "hola mundo" en un h1
Asistente: {"herramienta": "write_file", "argumentos": {"ruta": "hola.html", "contenido": "<!DOCTYPE html>\n<html>\n<head><meta charset='utf-8'><title>Hola</title></head>\n<body>\n<h1>hola mundo</h1>\n</body>\n</html>\n"}, "pensamiento": "creo html completo"}

REGLA: respondé SOLO el JSON (o TERMINADO:). NADA antes ni después. Sin markdown.

REGLAS DE CONTENIDO (CRÍTICAS):
- El campo "contenido" del JSON debe contener el archivo ENTERO y VÁLIDO, desde la primera línea hasta la última.
- NUNCA devuelvas solo un fragmento, un <script> aislado, o porciones del archivo. Integralidad obligatoria.
- HTML completo: incluí <!DOCTYPE html>, <html>, <head>, <style>, <body>, <script>.
- Cierra SIEMPRE todas las etiquetas y llaves.
- Para "agregá/modificá X": primero read_file, luego devolvé el archivo ENTERO modificado.
- Rutas relativas simples: "main.py", "carpeta/arch.py".
- Sin placeholders ni "...resto del código aquí"."""


def obtener_modelos_disponibles():
    """Consulta los modelos disponibles en Ollama."""
    try:
        url = OLLAMA_URL.replace("/api/chat", "/api/tags")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        modelos = response.json().get("models", [])
        return [m["name"] for m in modelos]
    except Exception:
        return [MODELO_CODER]  # Fallback

def preguntar_coder(prompt_usuario, historial=None, modelo_seleccionado=None):
    """Envía la consulta a Ollama con timeout extendido."""
    if historial is None:
        historial = []
    
    # Usar modelo seleccionado si se proporciona, sino el default
    modelo = modelo_seleccionado or MODELO_CODER
    
    messages = [{"role": "system", "content": PROMPT_SISTEMA}] + historial + [{"role": "user", "content": prompt_usuario}]
    
    data = {
        "model": modelo,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 16384
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=300)
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "❌ TIMEOUT: El modelo tardó más de 5 minutos."
    except requests.exceptions.ConnectionError:
        return "❌ ERROR: No se pudo conectar con Ollama."
    except Exception as e:
        return f"❌ Error: {str(e)}"


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
        if "herramienta" in data and "argumentos" in data:
            return data
        return None
    except json.JSONDecodeError:
        return None