import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.command_runner import validar_comando
from core.file_manager import escribir_archivo, leer_archivo
from core.security import validar_ruta_segura
from core.workspace_context import explorar_workspace
from core.coder_agent import forzar_json


class CoreTests(unittest.TestCase):
    def test_path_traversal_and_absolute_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root) / "base"
            base.mkdir()
            sibling = Path(root) / "base_evil" / "payload.py"
            self.assertFalse(validar_ruta_segura(str(base), "../base_evil/payload.py")[0])
            self.assertFalse(validar_ruta_segura(str(base), str(sibling))[0])

    def test_normal_nested_path_is_allowed(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root) / "base"
            base.mkdir()
            self.assertTrue(validar_ruta_segura(str(base), "src/main.py")[0])

    def test_write_and_read_utf8_file(self):
        with tempfile.TemporaryDirectory() as root:
            ok, _ = escribir_archivo(root, "src/hola.py", "print('¡hola!')\n")
            self.assertTrue(ok)
            content, error = leer_archivo(root, "src/hola.py")
            self.assertEqual(error, "")
            self.assertEqual(content, "print('¡hola!')\n")
            self.assertFalse(list((Path(root) / "src").glob(".autocoder-*")))

    def test_dangerous_commands_are_rejected(self):
        cases = [
            ["powershell", "-Command", "whoami"],
            ["git", "reset", "--hard"],
            ["python", "../outside.py"],
            ["python", str(Path.home() / "outside.py")],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                self.assertFalse(validar_comando(argv)[0])

    def test_validation_commands_are_allowed(self):
        for argv in (["python", "-m", "unittest"], ["git", "diff"], ["npm", "test"]):
            with self.subTest(argv=argv):
                self.assertTrue(validar_comando(argv)[0])

    def test_sessions_are_persisted_atomically(self):
        import core.session_manager as sessions

        with tempfile.TemporaryDirectory() as root:
            data_dir = Path(root) / ".autocoder"
            sessions_dir = data_dir / "sessions"
            with patch.object(sessions, "DATA_DIR", data_dir), patch.object(sessions, "SESSIONS_DIR", sessions_dir):
                data = sessions.nueva_sesion(workspace=root, model="test-model")
                sessions.agregar_mensaje(data, "user", "Crear una aplicación de prueba")
                sessions.guardar_sesion(data)
                loaded = sessions.cargar_sesion(data["id"])
                self.assertTrue(loaded["title"].startswith("Crear una aplicación"))
                self.assertEqual(loaded["messages"][0]["role"], "user")
                self.assertFalse(list(sessions_dir.glob("*.tmp")))

    def test_workspace_explorer_returns_tree_contents_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "app.py").write_text("print('programa real')\n", encoding="utf-8")
            Path(root, ".env").write_text("SECRET=no-debe-salir\n", encoding="utf-8")
            snapshot, fingerprint = explorar_workspace(root)
            self.assertIn("app.py", snapshot)
            self.assertIn("programa real", snapshot)
            self.assertNotIn("SECRET", snapshot)
            self.assertEqual(len(fingerprint), 64)

    def test_json_parser_accepts_batch_actions(self):
        payload = '{"acciones":[{"herramienta":"write_file","argumentos":{"ruta":"a.py","contenido":"x"}}],"respuesta":"ok"}'
        parsed = forzar_json(payload)
        self.assertEqual(parsed["acciones"][0]["herramienta"], "write_file")

    def test_legacy_loop_messages_are_removed(self):
        from core.session_manager import limpiar_mensajes_del_loop

        data = {"messages": [
            {"role": "user", "content": "¿Qué programa es?"},
            {"role": "assistant", "content": "`list_files` · listar"},
            {"role": "tool", "content": "app.py"},
            {"role": "assistant", "content": "[Respuesta inválida del modelo; se solicitó JSON estricto]"},
            {"role": "assistant", "content": "Es una aplicación Streamlit."},
        ]}
        self.assertEqual(limpiar_mensajes_del_loop(data), 3)
        self.assertEqual([m["content"] for m in data["messages"]],
                         ["¿Qué programa es?", "Es una aplicación Streamlit."])

    def test_model_sync_persists_new_ollama_models(self):
        import core.provider_manager as providers

        provider = {
            "id": "ollama",
            "name": "Ollama local",
            "kind": "ollama",
            "base_url": "http://127.0.0.1:11434/api/chat",
            "models": ["modelo-anterior:latest"],
            "api_key_env": "",
        }
        response = unittest.mock.Mock()
        response.json.return_value = {
            "models": [
                {"name": "modelo-anterior:latest"},
                {"name": "modelo-nuevo:latest"},
            ]
        }
        response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as root:
            config_file = Path(root) / "providers.json"
            with patch.object(providers, "CONFIG_FILE", config_file), \
                    patch.object(providers.requests, "get", return_value=response):
                models, changed = providers.sincronizar_modelos(provider)
                saved = providers.cargar_proveedores()[0]

        self.assertTrue(changed)
        self.assertEqual(models, ["modelo-anterior:latest", "modelo-nuevo:latest"])
        self.assertEqual(saved["models"], models)

    def test_model_sync_does_not_overwrite_list_when_discovery_is_empty(self):
        import core.provider_manager as providers

        provider = {
            "id": "ollama",
            "kind": "ollama",
            "base_url": "http://127.0.0.1:11434/api/chat",
            "models": ["modelo-conocido:latest"],
        }
        with patch.object(providers, "descubrir_modelos", return_value=[]), \
                patch.object(providers, "guardar_proveedor") as save:
            models, changed = providers.sincronizar_modelos(provider)

        self.assertEqual(models, [])
        self.assertFalse(changed)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
