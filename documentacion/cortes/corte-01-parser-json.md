# Corte 01 — Refactor del parser JSON

## Fecha

2026-07-24

## Estado inicial

- rama: `main`
- HEAD: `aea2938`
- estado inicial del working tree: presentaban modificaciones no confirmadas en `.gitignore`, `LICENSE`, `app.py`, `auditoria-completa.md`, `core/cloud_processor.py`, `core/coder_agent.py`, `core/command_runner.py`, `core/drawers.json`, `core/drawers_manager.py`, `core/extensions_manager.py`, `core/file_manager.py`, `core/native_dialog.py`, `core/provider_manager.py`, `core/rag_manager.py`, `core/security.py`, `core/session_manager.py`, `core/workspace_context.py`, `index.html`, `requirements.txt`, `run.bat` y `test/test_core.py`.
- cambios previos del usuario que fueron preservados: todos los listados arriba; este corte los lee sin modificarlos y solo añade/cambia los archivos permitidos en el alcance.

## Objetivo

Separar el parser JSON (`forzar_json`) que vivía mezclado dentro del módulo legacy `core/coder_agent.py` para que pueda evolucionar de forma aislada y testeada, sin arrastrar el resto del código iterativo anterior.

## Alcance

Archivos creados durante el corte:

- `core/parsers.py`
- `test/test_parsers.py`
- `documentacion/cortes/corte-01-parser-json.md`

Archivos modificados durante el corte:

- `core/coder_agent.py` (convertido en shim)
- `app.py` (única línea de import)

## Decisiones técnicas

- `forzar_json` pasó a `core/parsers.py` porque es lógica pura de extracción de JSON, sin dependencias de Streamlit, de `requests`, de proveedores ni de ningún estado de `coder_agent.py`. Eso la convierte en una candidata natural a un módulo de utilidades testeable de forma aislada.
- Se mantuvo `core/coder_agent.py` solo como shim de compatibilidad para no romper el import legacy que ya usaba `test/test_core.py` (y que queríamos conservar como test real de compatibilidad). Sustituir el módulo completo fue seguro porque el grep global confirmó que ningún archivo del repositorio consume `PROMPT_SISTEMA`, `preguntar_coder`, `obtener_modelos_disponibles`, `OLLAMA_URL` ni `MODELO_CODER` desde ese módulo. Las referencias que el grep encontró a esos símbolos históricos viven sólo dentro de `core/coder_agent.py` o en `auditoria-completa.md`, que está fuera de alcance.
- La compatibilidad antigua se preserva reemplazando el cuerpo de `core/coder_agent.py` por un shim que reexporta `forzar_json` desde `core.parsers`. Así `from core.coder_agent import forzar_json` sigue funcionando sin código legacy activo.
- `test/test_core.py` conserva el import legacy deliberadamente: sirve como smoke test del shim. Modificarlo rompería el contrato del corte (el test debe seguir probando la compatibilidad con la ruta antigua).
- `{"respuesta":"ok"}` no es una acción válida por sí sola. El contrato exige o bien `herramienta` + `argumentos`, o bien `acciones` con valor lista. Por eso ese payload debe seguir devolviendo `None` y hay un test que lo verifica.
- Los símbolos legacy pudieron eliminarse del cuerpo de `core/coder_agent.py` sustituyendo el módulo entero por el shim. La búsqueda global no encontró consumidores, así que no fue necesario conservar `PROMPT_SISTEMA`, `preguntar_coder`, `obtener_modelos_disponibles`, `OLLAMA_URL` ni `MODELO_CODER` dentro del módulo.

## Cambios realizados

- `core/parsers.py` (nuevo): módulo mínimo con `import json`, `__all__ = ["forzar_json"]` y la función `forzar_json` trasladada tal cual desde `core/coder_agent.py`. Sin imports de Streamlit, requests, dotenv ni módulos internos.
- `core/coder_agent.py` (shim): sustituido por un reexport desde `core.parsers`. Conserva `__all__ = ["forzar_json"]` y la docstring de compatibilidad.
- `app.py`: reemplazada exclusivamente la línea `from core.coder_agent import forzar_json` por `from core.parsers import forzar_json`. Ningún otro cambio.
- `test/test_parsers.py` (nuevo): tests `unittest` que importan `forzar_json` desde `core.parsers` y cubren acción simple, code fence, texto alrededor, batch de acciones, JSON sin estructura de acción, prosa sin JSON, JSON inválido y llaves dentro de strings.
- `documentacion/cortes/corte-01-parser-json.md` (nuevo): este documento.

## Validación

Comandos ejecutados (Windows PowerShell 5.1, ejecutable: `python`, versión reportada `Python 3.14.6`):

- `python -m compileall core app.py test` — exit code `0`. Compiló sin errores todos los módulos de `core/` (incluido `core/parsers.py` y `core/coder_agent.py` ya como shim), `app.py` y los dos archivos de `test/`.
- `python -m unittest discover -s test -v` — exit code `0`. Ejecutó 19 tests, todos `ok`: 11 existentes en `test_core` (incluido `test_json_parser_accepts_batch_actions` que sigue importando `forzar_json` desde `core.coder_agent` y verifica que el shim funciona) y los 8 nuevos en `test_parsers`.
- `python -m unittest test.test_parsers -v` — la forma `test.test_parsers` no funciona con `unittest` en este entorno porque el directorio `test/` no es un paquete (no existe `test/__init__.py`). Es un detalle del runner, no del parser. La validación equivalente y ejecutada es `python -m unittest discover -s test -v`, que descubrió y ejecutó correctamente los 8 tests de `TestForzarJson`.

Resultado bruto del discover (resumen): `Ran 19 tests in 4.367s — OK`.

## Estado final

- tests exitosos: 19 / 19.
- failures: 0.
- errors: 0.
- tests no ejecutados: ninguno.
- validaciones no ejecutadas: el comando `python -m unittest test.test_parsers -v` falla por la forma del nombre de módulo del runner, no por el parser. Se ejecutó la forma equivalente `python -m unittest discover -s test -v`, que cubre todos los tests previstos.
- riesgos o limitaciones: el parser sigue dependiendo de `json` de la biblioteca estándar y no agrega dependencias nuevas. No se modificaron archivos fuera del alcance. `test/test_core.py` continúa importando desde `core.coder_agent` y ese import sigue funcionando a través del shim (verificado por `test_json_parser_accepts_batch_actions`).

## Rollback

Para revertir manualmente este corte sin comandos destructivos:

1. Editar `core/coder_agent.py` y restaurar el contenido anterior completo (incluyendo `PROMPT_SISTEMA`, `obtener_modelos_disponibles`, `preguntar_coder` y la definición local de `forzar_json`).
2. Borrar `core/parsers.py`.
3. En `app.py`, reemplazar `from core.parsers import forzar_json` por `from core.coder_agent import forzar_json`.
4. Borrar `test/test_parsers.py`.
5. Borrar `documentacion/cortes/corte-01-parser-json.md`.

`test/test_core.py` no requiere cambios porque nunca se modificó durante este corte.

## Próximo corte sugerido

- Como propuesta pendiente, no implementada:
  - Documentación de instalación, `.env.example` y arranque multiplataforma, o bien
  - Configuración de contexto de Ollama.
