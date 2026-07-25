# Auditoría Completa — Programador-Autónomo-Local

> **Proyecto**: AutoCoder Studio  
> **Fecha de auditoría**: 2026-07-24  
> **Propósito**: Documentación exhaustiva para que otro LLM comprenda el proyecto sin acceso al código fuente.

---

## 1. Resumen Ejecutivo

**AutoCoder Studio** es un agente de codificación **local, privado y human-in-the-loop (HITL)** construido sobre **Streamlit**. Se conecta a LLMs locales vía **Ollama** (o proveedores cloud **OpenAI**/Anthropic configurables).

### Flujo de alto nivel
1. Usuario selecciona un **workspace** (carpeta local).
2. La app explora el workspace y construye un **snapshot** (árbol + contenido de archivos relevantes).
3. Opcionalmente añade contexto desde una **base RAG local** (ChromaDB + embeddings Ollama).
4. Consulta al modelo con un system prompt anti-injection muy cuidadoso.
5. El modelo devuelve **análisis en prosa** (modo lectura) o **propuesta JSON de acciones** (modo cambio).
6. **Siempre pide aprobación humana** antes de tocar el filesystem o ejecutar comandos.
7. Al aprobar, ejecuta las acciones (escritura/borrado/comandos whitelisted).

### Filosofía de diseño
- **One-shot por aprobación** (no loop iterativo — migró desde un diseño legacy con `MAX_ITER=20`).
- **Seguridad primero**: anti-path-traversal, anti-prompt-injection, whitelist de comandos, escritura sin shell.
- **Persistencia atómica** en sesiones, proveedores y archivos (`tempfile.mkstemp` + `os.fsync` + `os.replace`).
- **Privacidad**: fragmentación de documentos es local por defecto; el procesamiento cloud vía Gemini es optativo.

---

## 2. Estructura del Proyecto

```
Programador-Autonomo-Local/
├── .agents/                        [VACÍO — placeholder]
├── .autocoder/                     [DATOS RUNTIME — gitignored]
│   ├── chroma_db/
│   │   └── chroma.sqlite3          (188 KB — ChromaDB vector store)
│   ├── sessions/
│   │   └── 0bd588abf5624cb6b92270a9b384f8c7.json  (838 B)
│   ├── skills/                     [VACÍO — skills .md bajo demanda]
│   └── providers.json              (525 B)
├── core/
│   ├── __init__.py                 (vacío — marca paquete)
│   ├── cloud_processor.py          (107 líneas)
│   ├── coder_agent.py              (166 líneas — parcialmente legacy)
│   ├── command_runner.py           (39 líneas)
│   ├── drawers.json                (config de taxonomía RAG)
│   ├── drawers_manager.py          (36 líneas — parcialmente legacy)
│   ├── extensions_manager.py       (84 líneas)
│   ├── file_manager.py             (131 líneas)
│   ├── native_dialog.py            (25 líneas)
│   ├── provider_manager.py         (142 líneas)
│   ├── rag_manager.py              (98 líneas)
│   ├── security.py                 (33 líneas)
│   ├── session_manager.py          (125 líneas)
│   └── workspace_context.py        (73 líneas)
├── documentacion/
│   └── pruebasdebbugprogramadorautonomo.docx  (24 KB)
├── test/
│   └── test_core.py                (147 líneas, 12 tests)
├── .env                            (265 bytes — gitignored)
├── .gitignore                      (86 bytes)
├── app.py                          (762 líneas — APLICACIÓN PRINCIPAL)
├── index.html                      (7.5 KB — workspace de ejemplo)
├── requirements.txt                (99 bytes)
└── run.bat                         (413 bytes)
```

### Excluido del versionado (`.gitignore`)
- `.env`, `__pycache__/`, `*.pyc`, `.streamlit/`, `chroma_db/`, `*.log`, `.DS_Store`, `Thumbs.db`, `.autocoder/`

---

## 3. Stack Tecnológico

### Dependencias Python (`requirements.txt`)
```
streamlit>=1.37.0
requests>=2.31.0
python-dotenv>=1.0.0
google-genai
chromadb
pypdf
python-docx
```

### Framework principal
- **Streamlit** — app interactiva de una sola página, lanzada con `streamlit run app.py` en `http://localhost:8501`.

### Otras librerías observadas en el venv
`pytest`, `uvicorn`, `httpx`, `websockets`, `huggingface-cli`, `typer`, `pygmentize`, `markdown-it`, `jsonschema`, `numpy`, `onnxruntime`, `transformers`, `sentence-transformers`, `watchdog`, altair, pydeck.

### Variables de entorno (`.env`) — solo nombres/claves
| Variable | Propósito |
|---|---|
| `OLLAMA_URL` | Endpoint Ollama chat (ej: `http://127.0.0.1:11434/api/chat`) |
| `MODELO_CODER` | Modelo default del coder (ej: `qwen2.5-coder:14b`) |
| `CARPETA_DEFECTO` | Workspace inicial por defecto (ruta absoluta) |
| `GOOGLE_API_KEY` | API key para Gemini (procesamiento cloud opcional) |

### Variables opcionales (en código, no en `.env`)
- `OLLAMA_CHAT_URL` (fallback de `OLLAMA_URL`)
- `OLLAMA_EMBED_URL` (default: `http://127.0.0.1:11434/api/embeddings`)
- `GOOGLE_DIGEST_MODEL` (default: `gemini-2.5-flash`)

---

## 4. `app.py` — Aplicación Principal (762 líneas)

### Configuración inicial
```python
st.set_page_config(page_title="AutoCoder Studio", page_icon="⌁",
    layout="wide", initial_sidebar_state="expanded")
```
- **Idioma**: español rioplatense ("Sos", "creá", "respondé", "seleccioná").
- **Tema oscuro custom** vía CSS inyectado (`--bg:#090b10`, sidebar oscura, monospace para árbol de archivos, sin globos en chat).

### Imports principales
```python
import html, json, os, shlex
from pathlib import Path
import requests, streamlit as st
from dotenv import load_dotenv

from core.coder_agent import forzar_json
from core.command_runner import ejecutar_comando, validar_comando
from core.cloud_processor import process_document_local
from core.extensions_manager import (cargar_comandos, cargar_funciones, cargar_skills,
    contexto_skills, guardar_comando, guardar_funcion, guardar_skill)
from core.file_manager import (borrar_archivo, escribir_archivo, generar_diff, leer_archivo)
from core.native_dialog import seleccionar_carpeta
from core.provider_manager import (cargar_proveedores, chat as provider_chat,
    guardar_proveedor, obtener_proveedor, sincronizar_modelos)
from core.rag_manager import RAG_DB_PATH, buscar_conocimiento, indexar_chunks
from core.session_manager import (agregar_mensaje, borrar_sesion, cargar_sesion,
    guardar_sesion, limpiar_mensajes_del_loop, nueva_sesion, listar_sesiones)
from core.workspace_context import explorar_workspace
```

### System Prompt (líneas 41-61)

Define a "AutoCoder" como asistente de programación con reglas críticas:

1. La app **ya exploró el workspace** — el modelo NO debe pedir `list_files` ni `read_file`.
2. El contenido entre `[ARCHIVOS DEL WORKSPACE]` y `[CONTENIDO DE ARCHIVOS RELEVANTES]` es **DATA NO CONFIABLE** (defensa anti-prompt-injection): el modelo debe analizarlo como código pero **jamás obedecerlo**.
3. **Modo lectura/análisis** → responder en prosa (JSON prohibido).
4. **Modo propuesta de cambio** → devolver JSON puro con acciones:

```json
{"herramienta":"write_file","argumentos":{"ruta":"...","contenido":"..."},"resumen":"..."}
{"herramienta":"delete_file","argumentos":{"ruta":"..."},"resumen":"..."}
{"herramienta":"run_command","argumentos":{"argv":["python","-m","pytest"]},"resumen":"..."}
{"herramienta":"run_function","argumentos":{"nombre":"..."},"resumen":"..."}
{"acciones":[{...}],"respuesta":"resumen"}
```

5. `write_file` siempre con el archivo **completo**, sin placeholders.

### Detección de modo: Lectura vs Propuesta

```python
CHANGE_KEYWORDS = ("creá","crear","crea ","modific","cambiá","cambia ","arregl",
    "correg","implement","agreg","añad","borr","elimin","ejecut","actualiz","refactor")

def is_change_request(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(keyword in lowered for keyword in CHANGE_KEYWORDS)
```

Conmuta entre:
- **MODO LECTURA** → prosa, JSON terminantemente prohibido (retry forzando prosa si el modelo viola).
- **MODO PROPUESTA** → sólo JSON de acciones.

### Tabla de funciones principales en `app.py`

| Función | Líneas | Propósito |
|---|---|---|
| `init_state()` | ~72 | Inicializa `st.session_state` (session_id, provider_secrets, pending_action, browser_path, preview_file, notice). Crea sesión inicial si no existe. |
| `session_data()` | ~78 | Carga sesión activa; si fue borrada, crea nueva. Limpia mensajes técnicos legacy. |
| `reset_runtime()` | ~88 | Limpia `pending_action`. |
| `switch_session(session_id)` | ~92 | Cambia sesión activa y resetea runtime. |
| `add_tool(data, content, success, tool)` | ~98 | Agrega mensaje de tipo `tool` con resultado de ejecución. |
| `css()` | ~104 | Inyecta CSS dark theme. |
| `render_model_selector(session_id, provider_id)` | ~127 | `@st.fragment(run_every="10s")` — sincroniza modelos Ollama cada 10s. |
| `render_provider_form(data)` | ~146 | Formulario para añadir proveedores (openai/anthropic/ollama). La API key NUNCA se persiste en disco, sólo en `session_state`. |
| `render_sidebar(data)` | ~195 | Sidebar completa: sesiones, proveedores, extensiones (cmd/skill/function), biblioteca RAG (upload PDF/DOCX/TXT). |
| `available_drives()` | ~256 | Lista unidades A-Z disponibles en Windows. |
| `set_workspace(data, path)` | ~261 | Resuelve ruta, valida directorio, persiste en sesión. |
| `render_folder_picker(data)` | ~269 | Selector de carpeta root: botón "Abrir Explorador Windows" (tkinter), navegación ↑, crear subcarpeta, listado. |
| `workspace_tree(workspace)` | ~320 | Genera árbol textual jerárquico (profundidad máx 3, 300 archivos máx). Ignora `node_modules`, `.venv`, `__pycache__`, `chroma_db`, carpetas con `.`. |
| `preview_candidates(workspace, limit=500)` | ~345 | Lista hasta 500 archivos (sin `.`, sin dirs ignorados). |
| `render_file_panel(data)` | ~355 | Panel derecho: folder picker + workspace bar + file tree + vista rápida de código. |
| `render_messages(data)` | ~410 | Render del chat (oculta mensajes `tool`). |
| `render_pending(data)` | ~440 | Muestra acción(es) propuesta(s) pendientes de aprobación con botones Aprobar/Rechazar. |
| `prepare_action(data, tool, args)` | ~475 | Valida/normaliza una acción propuesta → estructura interna con `tool`, `path`, `content`, `diff` / `argv`. |
| `answer_once(data, prompt)` | ~495 | **Núcleo del agente**: explora workspace → construye system + history → augmenta prompt con snapshot, memoria, RAG → llama proveedor → parsea JSON → retry si viola modo → prepara acción pendiente o responde en prosa. Acumula `input_tokens`/`output_tokens`. |
| `command_help()` | ~585 | Texto de ayuda para slash-commands. |
| `handle_command(data, raw)` | ~600 | Parser de slash-commands. |

### Slash-commands disponibles

| Comando | Descripción |
|---|---|
| `/new` | Nueva sesión |
| `/workspace RUTA` | Seleccionar workspace |
| `/model PROVEEDOR:MODELO` | Cambiar modelo activo |
| `/command NOMBRE :: PROMPT` | Comando reutilizable (`$ARGS` como placeholder) |
| `/skill NOMBRE :: DESCRIPCIÓN :: INSTRUCCIONES` | Skill inyectada al system prompt |
| `/function NOMBRE :: DESCRIPCIÓN :: COMANDO` | Función fija que siempre pide aprobación |
| `/stop` | Cancela propuesta pendiente |
| `/clear` | Limpia mensajes de la sesión |
| `/help` | Muestra ayuda |

### Flujo principal (líneas 710-762)

```python
init_state()
css()
data = session_data()
render_sidebar(data)

center, files = st.columns([3.5, 1.35])
with files: render_file_panel(data)
with center:
    # título + métricas tokens (IN/OUT/TOTAL)
    render_messages(data)
    render_pending(data)          # acciones pendientes de aprobación
    prompt = st.chat_input(...)
    if prompt:
        # si "stop"/"/stop" → cancela
        # si pending_action → la descarta (anti-bloqueo)
        # handle_command() decide si es slash-command o prompt normal
        # answer_once() con effective_prompt
        st.rerun()
```

---

## 5. Módulos `core/` — 13 archivos Python + 1 JSON

| Archivo | Líneas | Propósito | Estado |
|---|---|---|---|
| `__init__.py` | 0 | Marca `core/` como paquete Python | Activo |
| `coder_agent.py` | 166 | **Parser JSON legacy** + `forzar_json()` aún activo. El resto (loop iterativo, `preguntar_coder`, `PROMPT_SISTEMA` legacy) no se usa desde `app.py` | **Parcialmente legacy** |
| `command_runner.py` | 39 | Ejecución segura de comandos sin shell | Activo |
| `cloud_processor.py` | 107 | Procesamiento de documentos (fragmentación local + digestión cloud vía Gemini como alternativa) | Activo |
| `drawers_manager.py` | 36 | Taxonomía de "cajones" jerárquicos para RAG | **No importado por app.py** |
| `extensions_manager.py` | 84 | Sistema de extensiones declarativas (commands, functions, skills) | Activo |
| `file_manager.py` | 131 | Operaciones de archivo con validación anti-path-traversal y escritura atómica | Activo |
| `native_dialog.py` | 25 | Diálogo nativo de selección de carpeta vía tkinter | Activo |
| `provider_manager.py` | 142 | Multi-proveedor LLM con métricas de tokens normalizadas | Activo |
| `rag_manager.py` | 98 | Sistema RAG local con ChromaDB + embeddings vía Ollama | Activo |
| `security.py` | 33 | Validaciones de seguridad (rutas, extensiones, sanitización) | Activo |
| `session_manager.py` | 125 | Persistencia atómica de sesiones bajo `.autocoder/sessions/` | Activo |
| `workspace_context.py` | 73 | Exploración compacta del workspace con fingerprint SHA-256 | Activo |
| `drawers.json` | — | Taxonomía inicial: Python (FastAPI/Django/Pandas/IA), JavaScript (React/Node/Vue/TypeScript), General (Algoritmos/Arquitectura/Documentación) | Pasivo |

### Detalle de módulos clave

#### `coder_agent.py` — Parser JSON (`forzar_json`)
```python
def forzar_json(respuesta):
    # Quita code fences ```json ... ```
    # Busca primer '{' y último '}' balanceado respetando strings con escapes
    # Devuelve dict con "herramienta"+"argumentos" o "acciones":[...], o None
```
- Es el **único elemento activo** de este archivo. El resto (`PROMPT_SISTEMA` legacy, `preguntar_coder`, `obtener_modelos_disponibles`) son vestigios del diseño iterativo anterior.

#### `command_runner.py` — Whitelist de comandos
```python
ALLOWED = {"python", "pytest", "ruff", "node", "npm", "npx", "git", "gradlew"}
DENIED_GIT = {"add", "commit", "push", "pull", "checkout", "switch", "reset", "clean", "rm", "mv"}
```
- `validar_comando(argv)`: rechaza rutas absolutas y `..` fuera del workspace.
- `ejecutar_comando(workspace, argv, timeout=90)`: `subprocess.run` con `shell=False`, captura stdout+stderr, trunca a 20.000 caracteres.

#### `file_manager.py` — Operaciones atómicas seguras
```python
IGNORAR_DIRECTORIOS = {".git", ".venv", "node_modules", "__pycache__", "chroma_db"}
MAX_LECTURA_BYTES = 1_000_000  # 1 MB

def escribir_archivo(ruta_base, ruta_relativa, contenido):
    # Escritura atómica: tempfile.mkstemp + os.fsync + os.replace
    # Crea directorios padres automáticamente
    # Rechaza extensiones prohibidas (.exe, .bat, .sh, .dll, .so, .cmd)
```

#### `provider_manager.py` — Multi-proveedor LLM
- **3 formatos de API implementados**:
  - **ollama**: POST `/api/chat` con `temperature=0.1`, `num_ctx=32768`
  - **anthropic**: POST messages API con `x-api-key`, `max_tokens=8192`
  - **openai** (default): POST `/chat/completions` con `Authorization: Bearer`
- `sincronizar_modelos(provider, secrets, timeout)`: descubre modelos vía API y persiste sin cambiar el modelo activo.
- Token usage: si el proveedor no reporta, estima `max(1, len(text)//4)`.

#### `rag_manager.py` — RAG local con ChromaDB
```python
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
RAG_DB_PATH = ".../.autocoder/chroma_db"

def indexar_chunks(chunks, cajon, subcajon):
    # Inserta chunks con embeddings + metadatos (titulo, cajon, subcajon, importancia)

def buscar_conocimiento(query, cajon=None, subcajon=None):
    # Busca top-3 fragmentos por distancia vectorial
    # Devuelve string formateado "--- Fragmento (titulo) ---"
```

#### `session_manager.py` — Persistencia atómica de sesiones
```python
def nueva_sesion(workspace, provider_id, model):
    # Crea dict con id (UUID hex), title="Nueva sesión", messages=[], timestamps ISO UTC

def agregar_mensaje(data, role, content, **extra):
    # Append con timestamp. Auto-titula la sesión con primeros 52 chars del primer mensaje user.

def limpiar_mensajes_del_loop(data):
    # Migración: remueve rastros técnicos del motor iterativo legacy
    # (role="tool", "[Respuesta inválida", "[Finalización rechazada", "TERMINADO:", etc.)
```

#### `workspace_context.py` — Snapshot con fingerprint
```python
IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__", "chroma_db", ".autocoder", "dist", "build"}
TEXT_EXTENSIONS = 31 extensiones de código (.py, .js, .ts, .tsx, .html, .css, .vue, .svelte, .sql, .xml, .yaml, etc.)
IMPORTANT_NAMES = archivos prioritarios (readme.md, requirements.txt, package.json, app.py, main.py, index.html, etc.)

def explorar_workspace(workspace, max_chars=60_000):
    # 1. Lista archivos relativos (máx 600)
    # 2. Calcula fingerprint SHA-256 (concatena "rel:tamano:mtime_ns" — detecta cambios)
    # 3. Construye árbol textual + contenido de archivos relevantes
    #    (prioriza IMPORTANT_NAMES, límite 250 KB/archivo, excerpt 12.000 chars)
    # 4. Devuelve (snapshot, fingerprint)
    #    con secciones [ARCHIVOS DEL WORKSPACE] y [CONTENIDO DE ARCHIVOS RELEVANTES]
```

#### `security.py` — Validaciones
```python
EXTENSIONES_PROHIBIDAS = {'.exe', '.bat', '.sh', '.dll', '.so', '.cmd'}

def validar_ruta_segura(ruta_base, ruta_archivo):
    # Rechaza absolutos, normaliza con os.path.realpath, comprueba commonpath
    # (anti-symlink, anti-../)

def sanitizar_nombre_archivo(nombre):
    # re.sub(r'[^a-zA-Z0-9_\-.]', '_', nombre)
```

#### `cloud_processor.py` — Procesamiento de documentos
- **Dos pipelines**:
  - `process_document_cloud(...)`: usa Gemini 2.5-flash para chunking semántico (requiere `GOOGLE_API_KEY`).
  - `process_document_local(...)`: fragmentación determinista (corta por párrafos `\n\n` hasta 1800 chars). **Es la que usa app.py** (privacidad primero).
- Extrae texto de PDF (pypdf), DOCX (python-docx), TXT.

---

## 6. Tests — `test/test_core.py` (147 líneas, 12 tests)

Framework: **unittest** (sin pytest fixtures).

| Test | Cobertura |
|---|---|
| `test_path_traversal_and_absolute_paths_are_rejected` | Seguridad: `validar_ruta_segura` rechaza `../base_evil/payload.py` y rutas absolutas |
| `test_normal_nested_path_is_allowed` | `src/main.py` pasa validación |
| `test_write_and_read_utf8_file` | Escritura/lectura de UTF-8 con acentos; verifica que no queden `.autocoder-*` temp files |
| `test_dangerous_commands_are_rejected` | Bloquea `powershell -Command whoami`, `git reset --hard`, `python ../outside.py`, rutas absolutas |
| `test_validation_commands_are_allowed` | Permite `python -m unittest`, `git diff`, `npm test` |
| `test_sessions_are_persisted_atomically` | Persistencia atómica de sesiones; verifica título auto-generado y ausencia de archivos `.tmp` |
| `test_workspace_explorer_returns_tree_contents_and_fingerprint` | Snapshot incluye contenido de `app.py` pero NO de `.env` (no filtra secretos); fingerprint 64 chars |
| `test_json_parser_accepts_batch_actions` | `forzar_json` parsea `{"acciones":[...],"respuesta":"ok"}` |
| `test_legacy_loop_messages_are_removed` | `limpiar_mensajes_del_loop` elimina 3 mensajes técnicos, deja 2 válidos |
| `test_model_sync_persists_new_ollama_models` | Mockea `requests.get` con 2 modelos, `sincronizar_modelos` detecta cambios y persiste |
| `test_model_sync_does_not_overwrite_list_when_discovery_is_empty` | Descubrimiento vacío NO persiste ni llama `guardar_proveedor` |

**Cobertura faltante**: `rag_manager`, `cloud_processor`, `extensions_manager`, `native_dialog`, UI Streamlit.

---

## 7. Documentación — `documentacion/pruebasdebbugprogramadorautonomo.docx`

- **Autor**: Charly Alonso (metadatos `cp:coreProperties`).
- **Fechas**: creado 2026-07-08, modificado 2026-07-09.
- **Título**: "Serie A — Pruebas del problema sin solución / Debug del Programador Autónomo".

### Contenido clave — Historia evolutiva

Documenta bugs y experimentos del diseño **iterativo legacy** (con `MAX_ITER=20`, `TERMINADO:`, bucle automático) y cómo se migró al diseño **one-shot por aprobación** actual.

| Prueba | Problema | Solución / Estado |
|---|---|---|
| **Intento 1** — P vs NP (test anti-bloqueo) | El modelo respondió `TERMINADO:` inmediatamente copiando el placeholder del system prompt. Sin bucle. | ?? |
| **Intento 2** — Contador 1→50 | El modelo **simuló** haber ejecutado 50 iteraciones en un único paso (sin invocar `write_file`). | **FALLIDO** (Execution Hallucination) |
| **Intento 3** — Shortcut Hallucination | El modelo salta al resultado final sin pasos intermedios. El archivo físico sólo contenía "1". | **FALLIDO** |
| **Intento .7** — Refuerzo de Memoria | Inyectando el estado actual del archivo en cada prompt, el agente ejecutó el ciclo Leer→Sumar→Escribir correctamente hasta `MAX_ITER=20`. | **EXITOSO** |
| **Test 4** — Rechazo de archivos | El sistema forzó el cierre del loop al detectar "Reescritura Idéntica" tras rechazos repetidos. | **FALLIDO / EDGE CASE** |
| **Prueba 2** — Instrucciones contradictorias | El agente intentó `delete_file` pero el sistema respondió "Herramienta desconocida". Se implementó `borrar_archivo()`. Tras la corrección, el modelo omitió el último `read_file`. | **PARCIALMENTE EXITOSO** |
| **Prueba 3** — Sobre-alineación | El agente se negó a sugerir configuración por "miedo a alucinar". | Se introdujeron **Modo Estricto** y **Modo Proactivo** (trigger por keywords como "sugerime", "proponé"). **EXITOSO** tras el ajuste |
| **Test 5** — Persistencia del objetivo | El modelo cerró con `TERMINADO:` ignorando 3 instrucciones adicionales del usuario ("Agente Fantasma" de Qwen 14B). | **FALLIDO** |
| **Prueba 5 fase 2** — Interrupción Humana | Si el usuario escribe mientras el agente espera aprobación, el sistema ignora el nuevo mensaje. | Se implementó detector de interrupciones con 3 botones (Replantear, Cancelar, Ignorar). **HITL blindado** |

### Conclusión de la documentación
Esta documentación explica **por qué** el proyecto actual es one-shot en vez de iterativo: las hallucinations de ejecución, el "Agente Fantasma" (que cierra prematuramente), y la necesidad de human-in-the-loop llevaron a rediseñar completamente la arquitectura.

---

## 8. Archivos Complementarios

### `index.html` (7.5 KB)
- **No es parte del runtime** de AutoCoder Studio.
- Es un archivo **estático de ejemplo** que sirve como workspace de prueba para el agente.
- Implementa una **calculadora de dólar tarjeta e importación argentina** con dos pestañas en CSS puro.
- Características: fetch a `https://dolarapi.com/v1/dolares/tarjeta`, `Intl.NumberFormat('es-AR')`, fallback a 1500.
- Está en `IMPORTANT_NAMES` de `workspace_context.py`, por lo que el modelo lo recibe priorizado en los snapshots.

### `.agents/` — Vacío
Directorio placeholder trackeado por git. No referenciado desde el código. Probablemente reservado para futuras integraciones.

### `.autocoder/` — Datos runtime (completamente gitignored)

Estructura actual:
```
.autocoder/
├── chroma_db/chroma.sqlite3        (188 KB — datos RAG persistidos)
├── sessions/
│   └── 0bd588abf5624cb6b92270a9b384f8c7.json
├── skills/                         [vacío]
└── providers.json                  (525 B)
```

**`providers.json`** — Proveedor persistido:
```json
[{
  "id": "ollama",
  "name": "Ollama local",
  "kind": "ollama",
  "base_url": "http://127.0.0.1:11434/api/chat",
  "models": [
    "deepseek-coder:6.7b", "mxbai-embed-large:latest", "nomic-embed-text:latest",
    "phi4:14b", "qwen2.5-coder:14b", "qwen2.5-coder:7b",
    "qwen2.5-coder:7b-instruct-q4_K_M", "qwen2.5-coder:latest",
    "qwen3.5:9b", "qwen3.5:9b-q4_K_M", "qwen3:30b-a3b", "qwen3:8b"
  ],
  "api_key_env": ""
}]
```
→ 12 modelos Ollama instalados localmente.

**Sesión persistida** (`0bd588...json`):
- Título: "podes leer lo que hay en esta carpeta y decirme que"
- Workspace: `C:\Users\delfa\Documents\programador en loop independiente` (otro proyecto)
- Modelo: `qwen2.5-coder:14b`
- 2 mensajes: pregunta + timeout (Read timed out)
- Timestamps: 2026-07-13

---

## 9. Arquitectura General

### Diagrama de componentes y flujo de datos

```
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT UI (app.py)                                         │
│ ┌──────────────────┐  ┌────────────────────┐                 │
│ │ Sidebar          │  │ Main (chat)        │                 │
│ │ - Sesiones       │  │ - Chat history     │                 │
│ │ - Providers      │  │ - Pending action   │                 │
│ │ - Extensiones    │  │ - Tokens métricas  │                 │
│ │ - Biblioteca RAG │  │ - File explorer    │                 │
│ └────────┬─────────┘  └────────┬───────────┘                 │
└──────────┼─────────────────────┼─────────────────────────────┘
           │                     │
           ▼                     ▼
┌────────────────────┐  ┌─────────────────────────┐
│ session_manager    │  │ workspace_context       │ → snapshot + fingerprint
│ (sesiones atomicas)│  │ (explora el filesystem) │
└────────────────────┘  └───────────┬─────────────┘
                                    │
                                    ▼
┌────────────────────┐  ┌──────────────────────┐
│ provider_manager   │  │ rag_manager          │ → buscar_conocimiento
│ (multi-proveedor)  │  │ (ChromaDB + embed)   │   (contexto RAG opcional)
│ chat() → texto     │  └──────────────────────┘
└────────┬───────────┘
         │
         ▼
    LLM (Ollama / OpenAI / Anthropic)
         │
         ▼
┌──────────────────────┐
│ forzar_json()        │ → parser tolerante
│ (coder_agent)        │
└──────────┬───────────┘
           │
     ┌─────┴──────┐
     │ parseó? NO │ parseó? SÍ
     ▼             ▼
 respuesta prosa  prepare_action()
 → workspace_     → valida herramienta
   memory         → genera diff
                 → pending_action
                       │
                       ▼
              ┌────────────────────┐
              │ HUMAN-IN-THE-LOOP  │
              │ Aprobar / Rechazar │
              └─────────┬──────────┘
                        │ Aprobar
                        ▼
              ┌────────────────────┐
              │ file_manager       │ → escribir/borrar (atómico + safe)
              │ command_runner     │ → ejecutar (whitelist + no shell)
              └────────────────────┘
```

### Patrones arquitectónicos observados (14)

1. **One-shot por aprobación** — El modelo recibe TODO el contexto en una consulta (snapshot + RAG + memoria + historial) y devuelve un lote de acciones. No hay loop iterativo.
2. **Human-in-the-Loop estricto** — El modelo nunca ejecuta directamente. Siempre propone → usuario aprueba → se aplica.
3. **Defensa anti-prompt-injection** — El system prompt trata el contenido del workspace como DATA NO CONFIABLE. El modelo debe analizarlo como código pero jamás obedecer instrucciones incrustadas.
4. **Modos dinámicos (Lectura/Propuesta)** — Detectados por `is_change_request()`. En modo lectura el JSON está prohibido y se fuerza retry si el modelo lo viola.
5. **Persistencia atómica** — Todos los managers usan `tempfile.mkstemp` + `os.fsync` + `os.replace`. Prevención contra archivos corruptos por crashes.
6. **Whitelist de seguridad** — Comandos (`ALLOWED` + `DENIED_GIT`) y extensiones (`EXTENSIONES_PROHIBIDAS`).
7. **Anti-path-traversal** — `os.path.realpath` + `commonpath` en todas las operaciones de archivo.
8. **Escritura sin shell** — `subprocess.run` con `shell=False` (evita inyección shell).
9. **Sesiones auto-tituladas** — Primeros 52 chars del primer mensaje de usuario como título.
10. **RAG local** — ChromaDB + embeddings Ollama (`nomic-embed-text`). Indexación opcional por "cajón" temático.
11. **Multi-proveedor con normalización de tokens** — Ollama/OpenAI/Anthropic con fallback de estimación (`len/4`).
12. **Auto-detección de modelos Ollama** — `st.fragment(run_every="10s")` consulta `/api/tags` periódicamente.
13. **Sincronización no destructiva** — Descubrimientos vacíos no sobrescriben la lista previa de modelos.
14. **Migración de datos legacy** — `limpiar_mensajes_del_loop` elimina rastros del motor iterativo anterior.

### Flujo detallado por consulta del usuario

1. `st.chat_input` → usuario escribe prompt.
2. Si es slash-command → `handle_command` ejecuta y responde en UI.
3. Si es prompt normal → `answer_once(data, effective_prompt)`:
   a. `obtener_proveedor(provider_id)` → recupera configuración del proveedor activo.
   b. `explorar_workspace(workspace)` → snapshot (árbol + contenidos relevantes) + fingerprint SHA-256.
   c. `cargar_funciones()` + `contexto_skills()` → extienden el system prompt con funciones y skills registrados.
   d. `is_change_request(prompt)` → decide modo (LECTURA = prosa / PROPUESTA = JSON).
   e. Construye mensajes: `system + history[-14:] + user(augmented con snapshot + memoria + RAG)`.
   f. `buscar_conocimiento(prompt)` → añade sección `[CONOCIMIENTO RAG RELEVANTE]` si existe.
   g. `provider_chat(...)` → llamada al LLM → respuesta + métricas de tokens.
   h. `forzar_json(response)` → intenta parsear.
   i. Si era modo LECTURA pero el modelo devolvió JSON → **retry** con meta-prompt forzando prosa (máx 2 intentos).
   j. Si no parsea → respuesta en prosa → se guarda en `workspace_memory` + `workspace_fingerprint` → se persiste la sesión.
   k. Si parsea → para cada acción: `prepare_action` valida y genera diff → `pending_action` en `session_state`.
4. UI renderiza `render_pending` con diffs → botones Aprobar/Rechazar.
5. Al Aprobar → ejecuta `escribir_archivo`/`borrar_archivo`/`ejecutar_comando` → resultado como mensaje `tool` → respuesta final al usuario como `assistant`.

---

## 10. Configuración y Deployment

### Ejecución (`run.bat`)
```bat
@echo off
echo Starting Autonomous Coder Agent...
echo Activating Virtual Environment...
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate
echo Installing/Updating dependencies...
pip install -r requirements.txt
echo.
echo Starting Streamlit App...
streamlit run app.py
pause
```
**Comando único**: doble-clic en `run.bat`. Crea venv si no existe, instala dependencias, lanza Streamlit en `http://localhost:8501`.

### Requisitos del sistema
1. **Python 3.14+**
2. **Ollama** corriendo en `127.0.0.1:11434` con modelos instalados (qwen2.5-coder, nomic-embed-text para RAG, etc.)
3. **Google API Key** (opcional, solo para procesamiento cloud vía Gemini)
4. **Tkinter** (viene con Python en Windows — necesario para el selector nativo de carpeta)
5. Java / Node / Git (opcional, si se quieren ejecutar comandos whitelisted)

### Variables de entorno necesarias (`.env`)
| Variable | Obligatoria | Propósito |
|---|---|---|
| `OLLAMA_URL` | Sí (default en código) | Endpoint chat de Ollama |
| `MODELO_CODER` | No (fallback a `qwen2.5-coder:7b`) | Modelo por defecto |
| `CARPETA_DEFECTO` | No | Workspace inicial |
| `GOOGLE_API_KEY` | No (solo cloud) | API key para Gemini |

### Persistencia
- `.autocoder/` se crea automáticamente en el directorio de ejecución.
- `chroma_db/` se inicializa lazy vía ChromaDB `PersistentClient`.
- Las API keys de proveedores adicionales se guardan **SÓLO en `st.session_state.provider_secrets`** (nunca en disco).
- `providers.json` contiene `api_key_env` (nombre de variable de entorno), nunca la key misma.
- Las sesiones no incluyen `provider_secrets`.

### Notas de seguridad operacional
- `GOOGLE_API_KEY` está en `.env` (gitignored).
- Los comandos git mutantes (`add`, `commit`, `push`, etc.) están explícitamente denegados.
- Las extensiones prohibidas (`.exe`, `.bat`, `.sh`, `.dll`, `.so`, `.cmd`) no pueden escribirse.
- Los archivos temporales `.autocoder-*` se limpian automáticamente (la escritura atómica usa `os.replace`).

---

## 11. Anexos

### Hallazgos curiosos
- **Python 3.14** en el venv (`cpython-314`) — versión muy nueva (aún en beta a mediados de 2026).
- La sesión guardada prueba el sistema con un workspace **distinto al proyecto actual** (otro directorio del usuario).
- El **fingerprint SHA-256** del workspace permite detectar cambios en el FS entre consultas (mecanismo de cache invalidation implícito, aunque no hay cache explícita).
- `drawers_manager.py` y `drawers.json` están definidos pero **no importados por `app.py`** — son utilidad para futuras extensiones de UI.
- `cloud_processor.py` tiene dos pipelines: la app usa la **local** por privacidad. El pipeline cloud (Gemini) es experimental y no está conectado a la UI.
- El usuario tiene **12 modelos Ollama** instalados localmente (deepseek-coder, mxbai-embed-large, nomic-embed-text, phi4, 5 variantes de qwen2.5-coder, qwen3.5 y qwen3).

### Deudas técnicas observadas
1. **`coder_agent.py` legacy**: mezcla `forzar_json()` (activo) con `PROMPT_SISTEMA` y `preguntar_coder` (no usados). Refactorizar moviendo `forzar_json` a `provider_manager.py` o un `parsers.py` nuevo.
2. **Test inconsistente**: `test/test_core.py` línea 108 importa `unittest.mock.Mock` inline en vez de usar el import de `unittest.mock` del encabezado.
3. **Cobertura de tests insuficiente**: `rag_manager`, `cloud_processor`, `extensions_manager`, `native_dialog` y toda la UI Streamlit no tienen tests.
4. **Sin logs**: no hay sistema de logging estructurado. Solo `print()` en `cloud_processor.py` y `rag_manager.py` para errores.
5. **`drawers_manager.py` huérfano**: no integrado con `app.py`, pese a que la taxonomía de cajones se usa conceptualmente en `rag_manager._collection_name()`.

---

*Fin de la auditoría. Este documento está diseñado para que un LLM comprenda completamente el proyecto AutoCoder Studio y pueda continuar el desarrollo, depuración o refactorización sin acceso directo al código fuente.*
