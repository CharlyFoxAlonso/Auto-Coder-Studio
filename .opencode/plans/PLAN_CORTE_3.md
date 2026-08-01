# Corte 3 — Extracción del parser de comandos

## Objetivo

Extraer únicamente la interpretación textual de comandos desde `app.py` hacia
`core/command_parser.py`: un módulo puro, determinista, sin Streamlit ni efectos.

```
texto bruto → parser/router puro → resultado estructurado → app.py ejecuta
```

---

## 1. Inventario exacto de comandos existentes

| # | Nombre | Alias | Sintaxis | Args esperados | Comportamiento actual |
|---|--------|-------|----------|----------------|----------------------|
| 1 | `help` | `commands` | `/help` | ninguno | Retorna ayuda textual (L629-641) |
| 2 | `new` | — | `/new` | ninguno | Crea sesión, switch, notice |
| 3 | `stop` | — | `/stop` | ninguno | `pending_action = None` |
| 4 | `clear` | — | `/clear` | ninguno | Vacía `messages`/tokens, guarda |
| 5 | `workspace` | — | `/workspace RUTA` | path | `set_workspace(rest.strip().strip('"'))` |
| 6 | `model` | — | `/model PROV:MOD` | `id:modelo` | `obtener_proveedor`, valida, guarda |
| 7 | `command` | — | `/command NOMBRE :: PROMPT` | `name :: prompt` | `guardar_comando(name, prompt)` |
| 8 | `skill` | — | `/skill N :: D :: I` | `n :: d :: i` | `guardar_skill(n, d, i)` |
| 9 | `function` | — | `/function N :: D :: C` | `n :: d :: cmd` | `shlex.split`, `validar_comando`, `guardar_funcion` |
| 10 | `connect` | — | `/connect` | ninguno | Mensaje: "usá paneles izquierda" (L703-704) |
| 11 | `models` | — | `/models` | ninguno | Idem |
| 12 | `sessions` | — | `/sessions` | ninguno | Idem |

Los comandos 1-9 son **comandos ejecutables**. Los comandos 10-12 son
**redirecciones a UI** (reconocidos, sin ejecución propia).

Además existe el caso de **comandos personalizados** (L649-651): se cargan desde
`cargar_comandos()` (disco → `dict[str, str]`). Si el nombre coincide, se
sustituye `$ARGS` y se retorna `(False, prompt)` para que el LLM lo procese.
Este caso **permanece en app.py** porque lee del disco.

---

## 2. Sintaxis y argumentos actuales

Cada comando se parsea así (L647-648):

```python
command, _, rest = raw[1:].partition(" ")
command = command.lower()
```

Luego cada bloque extrae sus propios argumentos de `rest`:

| Comando | Extracción de `rest` |
|---------|---------------------|
| help/commands | ignorado |
| new | ignorado |
| stop | ignorado |
| clear | ignorado |
| workspace | `rest.strip().strip('"')` |
| model | `rest.partition(":")` → `provider_id, sep, model` |
| command | `rest.partition("::")` → `name, sep, prompt` |
| skill | `rest.split("::", 2)` → `[name, desc, instr]` |
| function | `rest.split("::", 2)` → `[name, desc, cmd]` |
| connect/models/sessions | ignorado |

La extracción de argumentos es específica de cada comando y forma parte de la
**ejecución** (permanece en app.py). El parser solo separa `name` de `rest`.

---

## 3. Comportamiento actual ante comandos desconocidos

L705: `return True, f"Comando desconocido: \`/{command}\`. Escribí \`/help\`."`

El texto exacto se preserva. El parser reporta `UnknownCommand(name=...)` y
app.py formatea el mensaje.

Ante un comando personalizado que existe (L650-651): se sustituye `$ARGS` y se
retorna `(False, prompt_sustituido)`. El prompt sustituto se envía al LLM
en lugar del texto original. Esto permanece en app.py.

---

## 4. Bloque exacto de `app.py` que se movería

**NO** se mueve un bloque completo de código. Se extraen **tres elementos**
del interior de `handle_command` y de `command_help`:

### 4a. Catálogo de comandos (hoy implícito en if/elif)
Actualmente los nombres están dispersos en L653, L655, L661, L664, L670, L673,
L681, L687, L693, L703. En el nuevo módulo serán datos estáticos:

```python
# core/command_parser.py
COMANDOS: dict[str, CommandDef] = {
    "help": CommandDef(name="help", aliases=["commands"], syntax="/help", ...),
    "new": CommandDef(name="new", syntax="/new", ...),
    ...
}
```

### 4b. Lógica de detección y separación (L645-648)
```python
if not raw.startswith("/"):
    return False, raw
command, _, rest = raw[1:].partition(" ")
command = command.lower()
```
Se mueve a la función `parse()`.

### 4c. Comando desconocido + redirecciones UI (L653, L703-704)
El reconocimiento de nombres (`"help"`, `"commands"`, `"connect"`, etc.) y su
clasificación (ejecutable vs redirección) son datos del catálogo. Se mueven.

### 4d. `command_help()` (L629-641)
La ayuda textual se genera desde el catálogo en el nuevo módulo.

---

## 5. Bloque exacto que permanecería en `app.py`

**Todo el bloque de ejecución** dentro de cada `if` permanece (L655-702),
así como el manejo de comandos personalizados (L649-651) y el bloque `try/except`
(L652, L706-707).

La nueva `handle_command` en app.py:

```python
def handle_command(data: dict, raw: str) -> tuple[bool, str | None]:
    # --- PARSING (delegado al módulo nuevo) ---
    result = parse(raw)
    
    # --- CUSTOM COMMANDS (dinámicos, del disco) ---
    if isinstance(result, ParsedCommand) and result.kind != "not_a_command":
        custom = cargar_comandos()
        if result.name in custom:
            return False, custom[result.name].replace("$ARGS", result.args)
    
    # --- EJECUCIÓN (permanece) ---
    match result:
        case NotACommand():
            return False, raw

        case UnknownCommand(name=name):
            return True, f"Comando desconocido: `/{name}`. Escribí `/help`."

        case KnownCommand(name="help"):
            return True, generar_ayuda()

        case KnownCommand(name="new"):
            new = nueva_sesion(workspace=data.get("workspace", ""),
                               provider_id=data.get("provider_id", "ollama"),
                               model=data.get("model", ""))
            switch_session(new["id"])
            st.session_state.notice = ("success", "Nueva sesión creada.")
            return True, None

        case KnownCommand(name="stop"):
            st.session_state.pending_action = None
            return True, "Acción cancelada."

        case KnownCommand(name="clear"):
            data["messages"] = []
            data["input_tokens"] = data["output_tokens"] = 0
            guardar_sesion(data)
            reset_runtime()
            return True, "Sesión limpiada."

        case KnownCommand(name="workspace"):
            ok, message = set_workspace(data, result.args.strip().strip('"'))
            return True, message

        case KnownCommand(name="model"):
            provider_id, sep, model = result.args.partition(":")
            provider = obtener_proveedor(provider_id)
            if not sep or not provider or model not in provider.get("models", []):
                return True, "Usá `/model proveedor:modelo` con un modelo configurado."
            data["provider_id"], data["model"] = provider_id, model
            guardar_sesion(data)
            return True, f"Modelo activo: {provider_id}/{model}"

        case KnownCommand(name="command"):
            name, sep, prompt = result.args.partition("::")
            if not sep:
                return True, "Formato: /command nombre :: prompt"
            saved = guardar_comando(name.strip(), prompt.strip())
            return True, f"Comando `/{saved}` creado."

        case KnownCommand(name="skill"):
            parts = [part.strip() for part in result.args.split("::", 2)]
            if len(parts) != 3:
                return True, "Formato: /skill nombre :: descripción :: instrucciones"
            saved = guardar_skill(*parts)
            return True, f"Skill `{saved}` creada y activa para los próximos turnos."

        case KnownCommand(name="function"):
            parts = [part.strip() for part in result.args.split("::", 2)]
            if len(parts) != 3:
                return True, "Formato: /function nombre :: descripción :: comando"
            argv = shlex.split(parts[2], posix=os.name != "nt")
            ok, error = validar_comando(argv)
            if not ok:
                return True, error
            saved = guardar_funcion(parts[0], parts[1], argv)
            return True, f"Función `{saved}` creada. Su ejecución siempre pedirá aprobación."

        case KnownCommand(name="connect" | "models" | "sessions"):
            return True, "Usá los paneles de la izquierda para proveedores/modelos y sesiones."
```

Nota: la rama `connect/models/sessions` también podría manejarse mediante un
campo `kind="redirect"` en el `CommandDef` y un único `match`:

```python
case KnownCommand(kind="redirect"):
    return True, "Usá los paneles de la izquierda para proveedores/modelos y sesiones."
```

---

## 6. Contrato mínimo del resultado

```python
@dataclass
class NotACommand:
    raw: str

@dataclass
class UnknownCommand:
    raw: str
    name: str
    args: str

@dataclass
class KnownCommand:
    raw: str
    name: str
    args: str
    syntax: str
    descripcion: str
    kind: str  # "normal" | "redirect"

Parsed = NotACommand | UnknownCommand | KnownCommand
```

Propiedades del contrato:

| Propiedad | Garantía |
|-----------|----------|
| `name` | siempre minúscula |
| `args` | todo lo que sigue al nombre, sin strip (raw) |
| `kind` | `"normal"` para comandos ejecutables, `"redirect"` para connect/models/sessions |
| Inmutable | los objetos no se modifican después de creados |
| Sin `None` | todos los campos tienen valor |
| Sin Streamlit | ningún tipo importa `streamlit` |
| Sin archivos | ningún tipo contiene Path, IO, etc. |

---

## 7. Comparación de formatos del resultado

| Formato | Ventajas | Desventajas | Recomendación |
|---------|----------|-------------|---------------|
| `dict` | Sin imports extra, familiar | Sin tipado, campos discovery frágil, duck-typing en `match` | ❌ |
| `NamedTuple` | Inmutable, liviano, hashable | Sin métodos, herencia limitada | ❌ |
| `dataclass` (frozen) | Inmutable, métodos permitidos, `@dataclass(frozen=True)` seguro, `match` nítido, `kind` con `Literal` | Más boilerplate que dict | ❌ (bueno pero no óptimo) |
| `Union @dataclass` (recomendado) | Cada variante tiene solo sus campos, `match` exhaustivo con `type[]`, semántica explícita | Más tipos que una sola clase | ✅ |
| Función que retorna `tuple` | Minimalista | Sin semántica, posiciones frágiles | ❌ |

**Recomendación:** `Union` de tres `@dataclass(frozen=True)` — `NotACommand`,
`UnknownCommand`, `KnownCommand`. Cada uno con los campos estrictamente
necesarios. Uso con `match/case` en app.py.

---

## 8. Imports permitidos del nuevo módulo

```python
# Solo stdlib, sin efectos
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal  # opcional en Python 3.14+
```

**Prohibido explícitamente:**
- `streamlit` (prohibido por regla)
- `json`, `os`, `sys`, `pathlib`, `shlex` (efectos o parsing externo)
- `requests` (red)
- Cualquier `core.*` (dependencia del dominio)

El módulo no depende de ninguna otra parte del código. Es 100% autónomo.

---

## 9. Tests de comportamiento existente

Actualmente **no hay tests** para `handle_command`, `command_help`, ni
`prepare_action`. Solo se testean módulos de infraestructura:

| Archivo | Tests | Lo que testea |
|---------|-------|---------------|
| `test_core.py` | 12 | `validar_comando`, `validar_ruta_segura`, sesiones, workspace, `forzar_json` |
| `test_parsers.py` | — | (pendiente de leer) |
| `test_session_storage.py` | — | persistencia |

**Tests a crear en `test/test_command_parser.py` (~20-25 tests):**

### parse()
- `test_plain_text_returns_not_a_command` — `"hola"` → `NotACommand`
- `test_empty_string_returns_not_a_command` — `""` → `NotACommand`
- `test_slash_only_returns_unknown` — `"/"` → `UnknownCommand(name="")`
- `test_help_returns_known` — `"/help"` → `KnownCommand(name="help")`
- `test_commands_alias_returns_help` — `"/commands"` → `KnownCommand(name="help")`
- `test_case_insensitive` — `"/Help"` → `KnownCommand(name="help")`
- `test_new_returns_known` — `"/new"` → `KnownCommand(name="new")`
- `test_stop_returns_known` — `"/stop"` → `KnownCommand(name="stop")`
- `test_clear_returns_known` — `"/clear"` → `KnownCommand(name="clear")`
- `test_workspace_with_args` — `'/workspace /tmp'` → args=`"/tmp"`
- `test_model_with_args` — `'/model ollama:qwen'` → args=`"ollama:qwen"`
- `test_command_with_double_colon` — `'/command test :: echo hi'` → args=`"test :: echo hi"`
- `test_skill_with_triple_colon` — `'/skill a :: b :: c'` → args=`"a :: b :: c"`
- `test_function_with_triple_colon` — `'/function a :: b :: c'` → args=`"a :: b :: c"`
- `test_connect_returns_known_redirect` — `"/connect"` → `KnownCommand(kind="redirect")`
- `test_models_returns_known_redirect` — `"/models"` → `KnownCommand(kind="redirect")`
- `test_sessions_returns_known_redirect` — `"/sessions"` → `KnownCommand(kind="redirect")`
- `test_unknown_command` — `"/nonexistent"` → `UnknownCommand(name="nonexistent")`
- `test_args_never_stripped_in_parser` — `'/workspace   x'` → args=`"  x"` (raw)

### generar_ayuda()
- `test_generar_ayuda_matches_current_help_text` — compara string exacto

### Catálogo
- `test_all_command_names_are_lowercase`
- `test_no_duplicate_names`
- `test_all_aliases_resolve_to_existing_commands`

---

## 10. Tamaño estimado del diff

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `core/command_parser.py` | **Nuevo** | ~80-100 |
| `test/test_command_parser.py` | **Nuevo** | ~200-250 |
| `app.py` | Modificado | +5 / -15 (~20 líneas de diff neto) |
| `documentacion/cortes/corte-03-parsing-comandos.md` | **Nuevo** | (opcional, según política del proyecto) |
| **Total neto** | | ~300-370 líneas |

Detalle del cambio en `app.py`:
- **Eliminar:** `command_help()` (L629-641, ~13 líneas)
- **Reemplazar:** cuerpo de `handle_command` (L644-707, ~64 líneas) por versión
  que llama a `parse()` y ejecuta según resultado (~75 líneas)
- **Agregar import:** `from core.command_parser import parse, generar_ayuda`
- **Eliminar import:** ninguno (shlex, requests, etc. siguen siendo necesarios
  para la ejecución)

---

## 11. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Cambiar texto de ayuda** — si `generar_ayuda()` produce string diferente a `command_help()`, usuarios/tests existentes fallan | Medio | Probar que `generar_ayuda()` == `command_help()` exacto. Si el catálogo tiene el orden correcto y los mismos `—`, coincide. |
| **Case sensitivity** — `"/Help"` vs `"/help"` | Bajo | El `parse()` baja el case como hoy. Test explícito. |
| **Argumentos con espacios** — `'/workspace "C:\My Project"'` | Bajo | El parser no toca `rest`. app.py recibe el raw y hace `strip().strip('"')` como hoy. |
| **Alias `commands` desaparece** | Medio | Incluir en catálogo como alias de `help`. Test. |
| **`connect`/`models`/`sessions` dejan de funcionar** | Medio | Catalogarlos con `kind="redirect"`. Test. |
| **Regresión en main loop** — app.py L741-762 llama a `handle_command` | Alto | Suite completa `test/ -v` + smoke test manual. |
| **Comandos personalizados se rompen** — flujo L649-651 cambia | Alto | El chequeo de comandos personalizados se mantiene en app.py ANTES de llamar a `parse()`, con el mismo código. |

---

## 12. Criterios de aceptación

1. `python -m pytest test/ -v` — **25 tests existentes pasan** (0 failures)
2. `python -m pytest test/test_command_parser.py -v` — **tests nuevos pasan**
3. `python -c "from core.command_parser import parse, NotACommand, UnknownCommand, KnownCommand, generar_ayuda"` — import sin error
4. `python -c "from core.command_parser import *; print(generar_ayuda())"` — output coincide con `command_help()` actual
5. Todas las rutas de `handle_command` en app.py siguen produciendo los mismos
   strings de retorno para cada comando
6. Smoke test manual: ejecutar `streamlit run app.py` y probar `/help`, `/new`,
   `/stop`, `/clear`, `/workspace`, `/model`, `/command`, `/skill`,
   `/function`, texto plano, comando desconocido
7. Verificar que `/connect`, `/models`, `/sessions` siguen mostrando el mensaje
   de redirección a UI
8. Cualquier comando personalizado existente sigue funcionando
9. El nuevo módulo **no importa** `streamlit`, `os` (salvo quizás typing),
   `json`, `shlex`, `pathlib`, `requests`, ni ningún `core.*`

---

## 13. Veredicto

**VIABLE — parser puro.**

El parser cabe holgadamente en un módulo de ~90 líneas sin depender de
Streamlit, disco, red, ni otros módulos `core.*`. Todo lo que necesita es:

| Necesidad | Cómo la satisface |
|-----------|-------------------|
| Conocer comandos existentes | Catálogo estático `dict[str, CommandDef]` |
| Detectar `/` | `str.startswith("/")` |
| Separar nombre | `str[1:].partition(" ")` |
| Normalizar | `str.lower()` |
| Clasificar | lookup en catálogo + aliases |
| Representar resultados | 3 `@dataclass(frozen=True)` |
| Generar ayuda | bucle sobre catálogo |

**NO viable como parser + selección declarativa** porque las acciones de cada
comando tienen efectos laterales (sesiones, archivos, etc.) que no pueden
declararse sin arrastrar dependencias. La separación nítida es:

```
parser (puro) → result → app.py (match + ejecución)
```

---

## 14. Cortes posteriores (candidatos, no implementar)

### Corte 4 — Separación de `answer_once` y coordinación con el modelo
Extraer la lógica de interacción con el proveedor LLM: armado de system prompt,
history window, llamada a `provider_chat`, manejo de read-only mode, parsing
de respuesta (`forzar_json`), y lógica de reintento. Dejaría en app.py solo
el wrapper con `st.spinner` y la aplicación del resultado a `st.session_state`.

### Corte 5 — Separación de clasificación/preparación de acciones
`prepare_action` e `is_change_request` forman una frontera natural:
clasificar si un prompt pide cambio y preparar acciones validadas. Podrían
formar `core/action_preparer.py` o similar, independiente del parser y del
coordinador LLM.

### Corte futuro — Ubicación de `SYSTEM_PROMPT`
El prompt del sistema (~25 líneas) es configuración, no código. Podría
moverse a `core/prompts.py` o a un archivo de configuración, pero no hay
urgencia mientras sea estable.
