# Corte 02 — Persistencia de sesiones

## Fecha
2026-07-25

## Precheck
- rama: `main`
- HEAD (abreviado): `aea2938`
- working tree inicial: 28 archivos modificados (principalmente cambios de fin‑de‑línea).
  `core/session_manager.py` solo tenía diferencias de fin de línea; no había cambios semánticos.

## Objetivo
Separar la responsabilidad *persistencia física* (creación de directorios, escritura/lectura atómica de JSON)
del dominio de sesión manteniendo la API pública de `core.session_manager` intacta.

## Evidencia del grafo (antes del corte)
- Funciones inspeccionadas: `guardar_sesion`, `cargar_sesion`, `nueva_sesion`, `agregar_mensaje`,
  `listar_sesiones`, `borrar_sesion`.
- Callers principales provienen de `app.py` (UI) y de los tests bajo `test/`.
- Callees internos: `_ensure`, `_path`, `_now`, `json.dump/load`, `tempfile.mkstemp`, operaciones de `os`.
- Relaciones `TESTS` conectan todas las funciones públicas con sus tests correspondientes.
- Hotspot relevante: `core.session_manager.guardar_sesion` (fan‑in 12).

## Responsabilidades antes del corte
| Símbolo | Responsabilidad | Usa disco | Usa JSON | API pública | Callers |
|---|---|---|---:|---:|---:|---|
| `nueva_sesion` | crear nueva sesión en memoria y delegar al guardado | no | no | sí | `app` |
| `agregar_mensaje` | mutar la estructura de la sesión | no | no | sí | `app`, tests |
| `guardar_sesion` | **persistencia** (serializar + escritura atómica) | sí | sí | sí | varios (UI, tests) |
| `cargar_sesion` | **persistencia** (lectura + deserialización) | sí | sí | sí | UI, tests |
| `listar_sesiones` | **persistencia** (enumerar archivos) | sí | sí | sí | UI, tests |
| `borrar_sesion` | **persistencia** (eliminar archivo) | sí | sí | sí | UI |
| `_ensure`, `_path`, `_now` | utilidades auxiliares (ruta, timestamp) | parcial | parcial | no | interno |

## Decisión técnica
Se identificó una frontera clara: todas las operaciones que interactúan con el sistema de archivos y con JSON
pueden reunirse en un módulo interno llamado **`core.session_storage`**. Las funciones de dominio
(`nueva_sesion`, `agregar_mensaje`, etc.) permanecen en `session_manager` y delegan a la nueva capa.

### Cambios implementados
- **Nuevo módulo** `core/session_storage.py` que contiene:
  - constantes `DATA_DIR`, `SESSIONS_DIR`
  - `_ensure`, `_session_path`
  - `save_session`, `load_session`, `list_sessions`, `delete_session`
- **`core/session_manager.py`** actualizado:
  - Importa la capa de storage.
  - `guardar_sesion`, `cargar_sesion`, `listar_sesiones`, `borrar_sesion` delegan a `session_storage`
    manteniendo la misma firma y comportamiento.
  - Se eliminaron los imports de `json`, `os` y `tempfile` que quedaron sin uso.
  - Docstring aclaratorio.
- **Nuevo test** `test/test_session_storage.py` cubre todas las operaciones de la capa de storage
  usando `tempfile.TemporaryDirectory` y `unittest.mock` para sobrescribir los directorios de datos.
- **Documentación** del corte creada (este archivo).

## Archivos creados
- `core/session_storage.py`
- `test/test_session_storage.py`
- `documentacion/cortes/corte-02-persistencia-sesiones.md`

## Archivos modificados
- `core/session_manager.py` (solo cambios internos, API pública sin alteración).
- `test/test_core.py` (solo el target de `patch`; ver sección *Corrección posterior*).

## API preservada
Los símbolos públicos (`nueva_sesion`, `guardar_sesion`, `cargar_sesion`, `listar_sesiones`,
`borrar_sesion`, `agregar_mensaje`, `limpiar_mensajes_del_loop`) siguen existiendo con la misma firma;
`app.py` sigue importándolos sin cambios.

## Tests ejecutados
```
python -m compileall core test                                          → OK
python -m unittest discover -s test -p "test_core.py" -v                 → 11 tests OK
python -m unittest discover -s test -p "test_session_storage.py" -v      → 6 tests OK
python -m unittest discover -s test -v                                   → 25 tests OK
```

## Grafo después del corte
- 271 nodos, 1034 relaciones.
- `core.session_storage` indexado como módulo con 5 funciones.
- `core.session_manager` importa 6 símbolos de `session_storage` (relaciones `IMPORTS`).
- No existe import directo `app.py → session_storage`.
- `test_session_storage.py` aparece como módulo de test.

## Compatibilidad
- `detect_changes` reporta 32 archivos modificados y 0 símbolos impactados (inconcluso, como se esperaba).

## Riesgos o pendientes
- La capa de storage asume que el directorio base es `.autocoder`; cualquier configuración externa
  que cambie esa ruta debe parchearse en los tests (actualmente cubierto con mock).

## Próximo corte sugerido
- Refactor de la lógica de expiración automática de sesiones o de limpieza de mensajes de bucle,
  manteniendo la separación de dominio vs persistencia.

## Corrección posterior

Durante la primera validación real se detectó que
`test_sessions_are_persisted_atomically` seguía parcheando
`DATA_DIR` y `SESSIONS_DIR` en `core.session_manager`.

Después de la extracción, esas constantes pertenecen y son consumidas por
`core.session_storage`.

El test se corrigió para parchear el módulo propietario real de las
constantes. No se modificó el comportamiento productivo ni la API pública.

También se eliminaron de `core.session_manager` los imports `json`, `os` y `tempfile` que quedaron sin
uso después de la extracción.

### Validación real de la corrección

```bash
python -m unittest test_core.CoreTests.test_sessions_are_persisted_atomically  # (usa discover)
python -m unittest discover -s test -p "test_core.py" -v                          # 11 tests OK
python -m unittest discover -s test -v                                            # 25 tests OK
```

Todos los tests de la suite completa pasan (exit code 0). No se escribió en
`$PWD/.autocoder/sessions/` porque los parches redirigen correctamente a directorios
temporales.

## Rollback
Para revertir manualmente este corte:
1. Restaurar `core/session_manager.py` desde HEAD (`git checkout HEAD -- core/session_manager.py`).
2. Eliminar `core/session_storage.py`.
3. Restaurar `test/test_core.py` desde HEAD.
4. Eliminar `test/test_session_storage.py`.
5. Eliminar este documento.
