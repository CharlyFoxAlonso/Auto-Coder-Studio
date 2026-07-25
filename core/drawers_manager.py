import json
import os

DRAWERS_FILE = os.path.join(os.path.dirname(__file__), "drawers.json")

def cargar_cajones():
    """Carga la jerarquía de cajones desde el archivo JSON."""
    if not os.path.exists(DRAWERS_FILE):
        # Valores por defecto si no existe
        return {
            "Python": {"FastAPI": [], "Django": []},
            "JavaScript": {"React": [], "Node.js": []}
        }
    try:
        with open(DRAWERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def guardar_cajones(data):
    """Guarda la jerarquía de cajones en el archivo JSON."""
    try:
        with open(DRAWERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def agregar_subcajon(cajon, subcajon):
    """Agrega un sub-cajón a un cajón existente."""
    data = cargar_cajones()
    if cajon not in data:
        data[cajon] = {}
    if subcajon not in data[cajon]:
        data[cajon][subcajon] = []
    return guardar_cajones(data)
