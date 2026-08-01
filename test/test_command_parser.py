"""Tests del parser puro de slash commands (Corte 3)."""
import unittest

from core.command_parser import (
    CATALOG,
    CommandDef,
    KnownCommand,
    NotACommand,
    ParsedCommand,
    UnknownCommand,
    generar_ayuda,
    parse,
)


EXPECTED_HELP = (
    "Comandos disponibles:\n\n"
    "- `/new` — nueva sesión\n"
    "- `/workspace RUTA` — seleccionar workspace\n"
    "- `/model PROVEEDOR:MODELO` — cambiar modelo\n"
    "- `/command NOMBRE :: PROMPT` — crear un comando reutilizable; usá `$ARGS`\n"
    "- `/skill NOMBRE :: DESCRIPCIÓN :: INSTRUCCIONES` — crear una skill\n"
    "- `/function NOMBRE :: DESCRIPCIÓN :: COMANDO` — crear una función fija aprobable\n"
    "- `/stop` — cancelar cualquier propuesta pendiente\n"
    "- `/clear` — limpiar mensajes de esta sesión\n"
    "- `/help` — mostrar esta ayuda\n"
)


class TextoNoComandoTests(unittest.TestCase):
    def test_texto_normal(self):
        result = parse("hola mundo")
        self.assertIsInstance(result, NotACommand)
        self.assertEqual(result.raw, "hola mundo")

    def test_cadena_vacia(self):
        result = parse("")
        self.assertIsInstance(result, NotACommand)
        self.assertEqual(result.raw, "")

    def test_texto_empieza_con_espacio_y_despues_slash(self):
        result = parse(" /help")
        self.assertIsInstance(result, NotACommand)
        self.assertEqual(result.raw, " /help")

    def test_texto_con_slash_en_medio(self):
        result = parse("hola /help")
        self.assertIsInstance(result, NotACommand)
        self.assertEqual(result.raw, "hola /help")


class ComandosConocidosTests(unittest.TestCase):
    def test_help(self):
        result = parse("/help")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "help")
        self.assertEqual(result.args, "")
        self.assertEqual(result.kind, "normal")

    def test_commands_es_alias_de_help(self):
        result = parse("/commands")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "help")
        self.assertEqual(result.kind, "normal")

    def test_new(self):
        result = parse("/new")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "new")
        self.assertEqual(result.kind, "normal")

    def test_stop(self):
        result = parse("/stop")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "stop")
        self.assertEqual(result.kind, "normal")

    def test_clear(self):
        result = parse("/clear")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "clear")
        self.assertEqual(result.kind, "normal")

    def test_workspace(self):
        result = parse("/workspace /tmp")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "workspace")
        self.assertEqual(result.args, "/tmp")
        self.assertEqual(result.kind, "normal")

    def test_model(self):
        result = parse("/model ollama:qwen2.5-coder")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "model")
        self.assertEqual(result.args, "ollama:qwen2.5-coder")
        self.assertEqual(result.kind, "normal")

    def test_command_con_doble_dos_puntos(self):
        result = parse("/command test :: echo hola")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "command")
        self.assertEqual(result.args, "test :: echo hola")

    def test_skill_triple_segmento(self):
        result = parse("/skill x :: desc :: instr")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "skill")
        self.assertEqual(result.args, "x :: desc :: instr")

    def test_function_triple_segmento(self):
        result = parse("/function x :: desc :: py test")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "function")
        self.assertEqual(result.args, "x :: desc :: py test")

    def test_connect_es_redirect(self):
        result = parse("/connect")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "connect")
        self.assertEqual(result.kind, "redirect")

    def test_models_es_redirect(self):
        result = parse("/models")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "models")
        self.assertEqual(result.kind, "redirect")

    def test_sessions_es_redirect(self):
        result = parse("/sessions")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "sessions")
        self.assertEqual(result.kind, "redirect")


class NormalizacionTests(unittest.TestCase):
    def test_nombre_en_mayusculas_se_normaliza(self):
        result = parse("/Help")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "help")

    def test_alias_en_mayusculas_se_normaliza(self):
        result = parse("/COMMANDS")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "help")

    def test_mayusculas_mixtas(self):
        result = parse("/NeW")
        self.assertIsInstance(result, KnownCommand)
        self.assertEqual(result.name, "new")

    def test_first_letter_capitalizada(self):
        result = parse("/Help")
        self.assertEqual(result.name, "help")


class ArgumentosTests(unittest.TestCase):
    def test_argumento_simple(self):
        result = parse("/workspace /tmp")
        self.assertEqual(result.args, "/tmp")

    def test_argumento_con_espacios_multiples_preserva_dos_espacios(self):
        result = parse("/workspace   x")
        self.assertEqual(result.args, "  x")

    def test_argumento_con_comillas(self):
        result = parse('/workspace "C:\\My Project"')
        self.assertEqual(result.args, '"C:\\My Project"')

    def test_argumento_con_doble_dos_puntos(self):
        result = parse("/command name :: prompt")
        self.assertEqual(result.args, "name :: prompt")

    def test_argumento_con_unicode(self):
        result = parse("/workspace /tmp/sección")
        self.assertEqual(result.args, "/tmp/sección")

    def test_argumento_vacio(self):
        result = parse("/help")
        self.assertEqual(result.args, "")

    def test_sin_espacio_despues_del_nombre(self):
        result = parse("/new")
        self.assertEqual(result.args, "")

    def test_espacios_al_final_se_preservan(self):
        result = parse("/workspace /tmp  ")
        self.assertEqual(result.args, "/tmp  ")

    def test_espacio_intermedio(self):
        result = parse("/model ollama:qwen")
        self.assertEqual(result.args, "ollama:qwen")


class DesconocidosTests(unittest.TestCase):
    def test_comando_inexistente(self):
        result = parse("/foo")
        self.assertIsInstance(result, UnknownCommand)
        self.assertEqual(result.name, "foo")
        self.assertEqual(result.args, "")

    def test_comando_inexistente_con_argumentos(self):
        result = parse("/foo bar baz")
        self.assertIsInstance(result, UnknownCommand)
        self.assertEqual(result.name, "foo")
        self.assertEqual(result.args, "bar baz")

    def test_slash_aislado(self):
        result = parse("/")
        # "/" produce name "" (porque "" no está en _INDEX) => UnknownCommand
        self.assertIsInstance(result, UnknownCommand)
        self.assertEqual(result.name, "")
        self.assertEqual(result.args, "")

    def test_comando_desconocido_con_espacios_y_unicode(self):
        result = parse("/café nada")
        self.assertIsInstance(result, UnknownCommand)
        self.assertEqual(result.name, "café")


class RedirectTests(unittest.TestCase):
    def test_connect_kind(self):
        self.assertEqual(parse("/connect").kind, "redirect")

    def test_models_kind(self):
        self.assertEqual(parse("/models").kind, "redirect")

    def test_sessions_kind(self):
        self.assertEqual(parse("/sessions").kind, "redirect")

    def test_help_kind(self):
        self.assertEqual(parse("/help").kind, "normal")

    def test_new_kind(self):
        self.assertEqual(parse("/new").kind, "normal")


class CatalogoTests(unittest.TestCase):
    def test_catalogo_es_iterable(self):
        self.assertIsInstance(CATALOG, tuple)
        self.assertGreater(len(CATALOG), 0)

    def test_nombres_canonicos_en_minusculas(self):
        for cmd in CATALOG:
            self.assertEqual(cmd.name, cmd.name.lower())

    def test_no_hay_nombres_duplicados(self):
        nombres = [cmd.name for cmd in CATALOG]
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_aliases_son_tuplas(self):
        for cmd in CATALOG:
            self.assertIsInstance(cmd.aliases, tuple)

    def test_aliases_resolubles(self):
        for cmd in CATALOG:
            for alias in cmd.aliases:
                self.assertEqual(alias, alias.lower())

    def test_orden_de_catalogo_para_ayuda(self):
        nombres = [cmd.name for cmd in CATALOG if cmd.kind == "normal"]
        self.assertEqual(
            nombres,
            ["new", "workspace", "model", "command", "skill", "function", "stop", "clear", "help"],
        )

    def test_alias_no_choca_con_otro_comando_ejecutable(self):
        """Ningún alias debe coincidir con el nombre canónico de OTRO comando ejecutable."""
        nombres_ejecutables = {cmd.name for cmd in CATALOG if cmd.kind == "normal"}
        for cmd in CATALOG:
            for alias in cmd.aliases:
                self.assertNotIn(
                    alias, nombres_ejecutables,
                    f"Alias '{alias}' de '{cmd.name}' colisiona con otro nombre canónico.",
                )

    def test_alias_no_choca_con_otro_redirect(self):
        nombres_redirect = {cmd.name for cmd in CATALOG if cmd.kind == "redirect"}
        for cmd in CATALOG:
            for alias in cmd.aliases:
                self.assertNotIn(alias, nombres_redirect)


    def test_todos_los_comandos_ejecutables_existen_en_catalogo(self):
        esperados_ejecutables = {
            "help", "new", "stop", "clear", "workspace", "model", "command", "skill", "function",
        }
        nombres = {cmd.name for cmd in CATALOG if cmd.kind == "normal"}
        self.assertEqual(nombres, esperados_ejecutables)

    def test_todos_los_redirects_existen_en_catalogo(self):
        esperados_redirect = {"connect", "models", "sessions"}
        nombres = {cmd.name for cmd in CATALOG if cmd.kind == "redirect"}
        self.assertEqual(nombres, esperados_redirect)

    def test_catalog_no_contiene_commands_personalizados(self):
        nombres = {cmd.name for cmd in CATALOG}
        # "" es reserved token vacío
        for nombre in nombres:
            self.assertTrue(nombre)
            self.assertNotIn("$ARGS", nombre)


class CommandDefTests(unittest.TestCase):
    def test_command_def_es_frozen(self):
        cmd = CATALOG[0]
        with self.assertRaises(Exception):
            cmd.name = "x"  # type: ignore[misc]

    def test_command_def_es_dataclass(self):
        self.assertTrue(hasattr(CommandDef, "__dataclass_fields__"))


class ParsedCommandTypesTests(unittest.TestCase):
    def test_tipos_resultado_congela_datos(self):
        na = NotACommand(raw="hola")
        self.assertEqual(na.raw, "hola")
        with self.assertRaises(Exception):
            na.raw = "x"  # type: ignore[misc]

    def test_unknown_congela_datos(self):
        u = UnknownCommand(raw="/foo", name="foo", args="")
        self.assertEqual(u.raw, "/foo")
        self.assertEqual(u.name, "foo")
        self.assertEqual(u.args, "")
        with self.assertRaises(Exception):
            u.name = "y"  # type: ignore[misc]

    def test_known_congela_datos(self):
        k = KnownCommand(raw="/help", name="help", args="",
                         syntax="/help", description="mostrar esta ayuda", kind="normal")
        with self.assertRaises(Exception):
            k.name = "y"  # type: ignore[misc]

    def test_parsed_command_es_union(self):
        from typing import get_origin, get_args
        args = get_args(ParsedCommand)
        self.assertEqual(set(args), {NotACommand, UnknownCommand, KnownCommand})


class AyudaTests(unittest.TestCase):
    def test_texto_exacto_de_la_ayuda_anterior(self):
        """Regresión: el texto debe coincidir byte por byte con command_help() original."""
        self.assertEqual(generar_ayuda(), EXPECTED_HELP)

    def test_ayuda_termina_en_salto_de_linea_unico(self):
        self.assertTrue(generar_ayuda().endswith("\n"))

    def test_ayuda_no_lista_redirects(self):
        for prohibida in ("/connect", "/models", "/sessions"):
            self.assertNotIn(prohibida, generar_ayuda())

    def test_ayuda_no_incluye_texto_commands(self):
        # /commands es alias de /help, no se muestra en la ayuda
        self.assertNotIn("/commands", generar_ayuda())


# ---------------------------------------------------------------
# LIMITACIÓN con tests de integración para handle_command
# ---------------------------------------------------------------
# Importar `app` dispara `from google import genai` (no instalado) y
# la inicialización global de Streamlit. Por lo tanto NO se pueden
# escribir tests directos de `handle_command` desde el módulo `app`
# en este corte, sin reescribir app.py (lo cual está fuera del alcance).
#
# Cobertura alternativa en este corte:
#   - 60 tests del parser puro (arriba).
#   - Tests del comportamiento de /help y /help_alias necesitan
#     ejecutarse manualmente con Streamlit (no automatizados aquí).
#
# Este límite se documenta en el archivo
# documentacion/cortes/corte-03-parsing-comandos.md.


if __name__ == "__main__":
    unittest.main()

