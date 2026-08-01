import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Import the storage module
from core import session_storage

class SessionStorageTests(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and patch the storage paths
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.patch_data_dir = mock.patch.object(session_storage, "DATA_DIR", Path(self.tmp_dir.name))
        self.patch_sessions_dir = mock.patch.object(session_storage, "SESSIONS_DIR", Path(self.tmp_dir.name) / "sessions")
        self.patch_data_dir.start()
        self.patch_sessions_dir.start()
        self.addCleanup(self.patch_data_dir.stop)
        self.addCleanup(self.patch_sessions_dir.stop)

    def test_guardar_y_cargar_sesion(self):
        data = {
            "id": "test123",
            "title": "Prueba",
            "messages": [{"role": "user", "content": "hola"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        # Guardar
        session_storage.save_session(data)
        # Verificar archivo creado
        session_file = session_storage._session_path(data["id"]).resolve()
        self.assertTrue(session_file.is_file())
        # Cargar y comparar
        loaded = session_storage.load_session(data["id"])
        self.assertEqual(loaded, data)

    def test_unicode_preservado(self):
        data = {"id": "u1", "title": "Título con áéíóú", "messages": []}
        session_storage.save_session(data)
        loaded = session_storage.load_session("u1")
        self.assertEqual(loaded["title"], data["title"])

    def test_cargar_inexistente_devuelve_none(self):
        self.assertIsNone(session_storage.load_session("no_existe"))

    def test_json_invalido_devuelve_none(self):
        # Crear archivo corrupto manualmente
        path = session_storage._session_path("corrupto")
        session_storage._ensure()
        path.write_text("{ invalid json", encoding="utf-8")
        self.assertIsNone(session_storage.load_session("corrupto"))

    def test_directorio_creado_automaticamente(self):
        # Parchar el directorio para que no exista aún
        self.assertFalse(session_storage.SESSIONS_DIR.exists())
        data = {"id": "auto", "title": "auto"}
        session_storage.save_session(data)
        self.assertTrue(session_storage.SESSIONS_DIR.is_dir())

    def test_guardar_dos_veces_sobrescribe(self):
        data = {"id": "dup", "title": "v1"}
        session_storage.save_session(data)
        data["title"] = "v2"
        session_storage.save_session(data)
        loaded = session_storage.load_session("dup")
        self.assertEqual(loaded["title"], "v2")

if __name__ == "__main__":
    unittest.main()
