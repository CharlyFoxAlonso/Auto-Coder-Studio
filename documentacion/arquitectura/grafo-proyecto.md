# Grafo estructural de Auto-Coder-Studio

## Fecha
2026-07-25

## Identidad del repositorio
- ruta analizada: `C:\Users\delfa\Documents\Auto-Coder-Studio`
- rama: `main`
- HEAD (abreviado): `aea2938`
- estado inicial del working tree: 27 archivos modificados (ver lista en sección *Impacto del working tree actual*)
- versión del MCP: **codebase‑memory‑mcp** (herramientas detectadas: `index_repository`, `list_projects`, `index_status`, `get_graph_schema`, `get_architecture`, `search_graph`, `query_graph`, `trace_path`, `detect_changes`, `search_code`, `search_graph`)
- nombre exacto del proyecto indexado: `C-Users-delfa-Documents-Auto-Coder-Studio`

## Estado de indexación
- estado: `ready`
- archivos indexados: **23** (`File` nodes)
- nodos totales: **235**
- relaciones totales: **919**
- warnings: ninguno reportado
- artefactos MCP generados automáticamente: `.codebase-memory/graph.db.zst` (creado por `index_repository`), `.gitattributes` **no** modificado

## Schema detectado
### Tipos de nodos
| etiqueta | cantidad |
|---|---:|
| Function | 77 |
| Variable | 42 |
| Method | 24 |
| File | 23 |
| Module | 22 |
| Section | 17 |
| Class | 7 |
| EnvVar | 7 |
| Package | 7 |
| Folder | 6 |
| Branch | 1 |
| Decorator | 1 |
| Project | 1 |

### Tipos de relaciones
| relación | cantidad |
|---|---:|
| DEFINES | 369 |
| CALLS | 242 |
| USAGE | 115 |
| IMPORTS | 42 |
| WRITES | 39 |
| TESTS | 31 |
| CONTAINS_FILE | 23 |
| DEFINES_METHOD | 19 |
| FILE_CHANGES_WITH | 10 |
| CONFIGURES | 9 |
| DEPENDS_ON | 7 |
| SEMANTICALLY_RELATED | 6 |
| CONTAINS_FOLDER | 4 |
| DECORATES | 1 |
| HAS_BRANCH | 1 |
| SIMILAR_TO | 1 |

## Resumen arquitectónico
- **entry points**: `app.py` (UI + orquestación), `core/parsers.forzar_json` (API JSON), `core/command_runner.ejecutar_comando` (ejecución segura), `core/session_manager.nueva_sesion` (persistencia).
- **paquetes externos** detectados: `chromadb`, `google‑genai`, `pypdf`, `python‑docx`, `python‑dotenv`, `requests`, `streamlit` (solo como dependencias, no como relaciones de import).
- **clusters (Leiden)** (muestra los más relevantes):
  - `core` (18 miembros, cohesión 0.473) – incluye funciones de gestión de archivos, seguridad, providers, RAG, session manager.
  - `test` (16 miembros, cohesión 0.486) – agrupa los tests y los módulos que prueban.
  - varios sub‑clusters de `core` con cohesión ≈ 0.5.
- **boundaries** (pares con mayor conteo de llamadas): `app ↔ session_manager` (25), `app ↔ dict` (11), `app ↔ extensions_manager` (10), `app ↔ file_manager` (4), etc.
- **hotspots** (funciones con mayor fan‑in según el grafo):
  1. `builtins.dict.get` (fan‑in 25)
  2. `builtins.len` (fan‑in 17)
  3. `builtins.list.append` (fan‑in 14)
  4. `core.session_manager.guardar_sesion` (fan‑in 12)
  5. `builtins.str.lower` (fan‑in 12)
  6. `core.parsers.forzar_json` (fan‑in 10)
  7. `core.session_manager.cargar_sesion` (fan‑in 6)
  8. `core.session_manager.agregar_mensaje` (fan‑in 5)
  9. `core.session_manager.nueva_sesion` (fan‑in 5)

## Inventario
| Tipo | Cantidad |
|---|---:|
| Archivos | 23 |
| Módulos | 22 |
| Clases | 7 |
| Funciones | 77 |
| Métodos | 24 |
| Tests detectados | 19 (funciones) + 2 clases = 21 símbolos de test |
| Rutas | 0 |
| Recursos | 0 |

## Dependencias entre módulos (IMPORTS)
- `app.py` importa **13** módulos diferentes (parsers, command_runner, cloud_processor, extensions_manager, file_manager, native_dialog, provider_manager, rag_manager, session_manager, workspace_context, etc.).
- Otros módulos poseen muy pocas imports (la mayoría 0‑1). Ejemplo: `core/security.py` no importa ningún módulo interno.
- **Módulo con más dependencias salientes**: `app.py` (13).
- **Módulo más importado**: `core/parsers.py` (importado por `app.py`, `core/coder_agent.py`, y varios tests).
- **Módulos sin imports internos**: `core/security.py`, `core/rag_manager.py` (solo usan stdlib y paquetes externos).
- **Ciclos de imports**: la consulta de ciclos no devolvió resultados; la herramienta MCP no soporta búsqueda de ciclos de longitud variable, por lo que no se pueden confirmar ciclos.

## Posibles ciclos
*No se pudieron verificar ciclos con la versión del MCP disponible.*

## Grafo de llamadas relevante
| Símbolo | Callers (hasta 2 hops) | Callees (hasta 2 hops) |
|---|---|---|
| `core.parsers.forzar_json` | `app.answer_once`, `app` (indirecto) | `builtins.len`, `builtins.range`, `builtins.dict.get` |
| `core.security.validar_ruta_segura` | `core.file_manager.listar_archivos`, `core.file_manager.leer_archivo`, `core.file_manager.escribir_archivo`, `core.file_manager.borrar_archivo`, `app.render_file_panel`, `core.file_manager.generar_diff`, `app.render_pending` | (ninguno) |
| `core.command_runner.validar_comando` | `app.prepare_action`, `app.handle_command`, `core.command_runner.ejecutar_comando`, `app.answer_once`, `app.render_pending` | `builtins.len`, `builtins.str.lower` |
| `core.command_runner.ejecutar_comando` | `app.render_pending`, `app` (indirecto) | `core.command_runner.validar_comando`, `builtins.len`, `builtins.str.lower` |
| `core.file_manager.escribir_archivo` | `app.render_pending`, `app` (indirecto) | `builtins.str`, `core.security.validar_ruta_segura`, `core.security.es_extension_segura`, `builtins.str.lower` |

## Relación entre producción y tests
- Se registraron **31** relaciones `TESTS` que conectan archivos de prueba con código productivo.
- Principales enlaces:
  - `test/test_parsers.py` → `core/parsers.forzar_json`
  - `test/test_core.py` → `core/command_runner.validar_comando`, `core/file_manager.escribir_archivo`, `core/file_manager.leer_archivo`, `core/security.validar_ruta_segura`, `core/workspace_context.explorar_workspace`, `core/coder_agent.forzar_json`, etc.
- No se encontró ninguna clase o función productiva sin al menos una relación `TESTS`; sin embargo, la ausencia de una relación no implica falta de cobertura (tests pueden ejercitar código indirectamente).

## Hotspots
- **Reportados por el MCP** (fan‑in > 10): los listados en la sección *hotspots* arriba.
- **Observaciones manuales**: `app.handle_command` y `app.answer_once` son puntos críticos de orquestación aunque no aparecen como hotspots porque el grafo cuenta llamadas a built‑ins.
- **Inferencias**: la alta fan‑in de `builtins` sugiere que gran parte del flujo depende de funciones de Python estándar; monitorizar cambios en esas áreas es poco útil.

## Impacto del working tree actual
`detect_changes` reportó 27 archivos modificados, sin símbolos de código impactados (profundidad 3). Esto indica que los cambios son mayormente de documentación, README, pruebas y archivos de configuración, sin tocar la lógica de la aplicación.

## Limitaciones del análisis
- No se evaluaron llamadas dinámicas (p.ej. `getattr`, importaciones condicionales) ni callbacks de Streamlit; el grafo está basado en análisis estático.
- La detección de ciclos de import no es soportada por la versión actual del MCP.
- Propiedades de complejidad (loop depth, etc.) no fueron usadas para este informe.
- La ausencia de relaciones `TESTS` no garantiza falta de cobertura; los tests pueden ejercitar código a través de rutas indirectas.

## Uso recomendado en próximos cortes
1. Ejecutar `index_repository` antes de cualquier análisis para mantener el grafo actualizado.
2. Consultar `get_graph_schema` para entender la versión del modelo antes de escribir consultas Cypher.
3. Utilizar `search_graph` para localizar símbolos antes de inspeccionarlos con `get_code_snippet`.
4. Emplear `trace_path` con direcciones `inbound` / `outbound` y profundidad adecuada para entender impacto de cambios.
5. Ejecutar `detect_changes` para obtener una visión rápida de archivos modificados en la rama de trabajo.
6. Verificar manualmente los hallazgos críticos (p.ej. funciones de seguridad, I/O) antes de cualquier refactor.

## Artefactos generados
- **Documento creado**: `documentacion/arquitectura/grafo-proyecto.md`
- **Artefactos automáticos del MCP**: `.codebase-memory/graph.db.zst` (creado al indexar). No se modificó `.gitattributes`.
- **Cambios previos del usuario**: mantenidos sin alteraciones.
