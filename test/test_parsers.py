import unittest

from core.parsers import forzar_json


ACCION_VALIDA = (
    '{"herramienta":"write_file",'
    '"argumentos":{"ruta":"a.py","contenido":"print(1)"},'
    '"resumen":"crear"}'
)


class TestForzarJson(unittest.TestCase):
    def test_accion_simple_valida(self):
        resultado = forzar_json(ACCION_VALIDA)

        self.assertIsInstance(resultado, dict)
        self.assertEqual(resultado["herramienta"], "write_file")
        self.assertEqual(resultado["argumentos"]["ruta"], "a.py")

    def test_json_con_code_fence(self):
        texto = f"```json\n{ACCION_VALIDA}\n```"

        resultado = forzar_json(texto)

        self.assertIsInstance(resultado, dict)
        self.assertEqual(resultado["herramienta"], "write_file")

    def test_json_con_texto_alrededor(self):
        texto = f"Resultado propuesto: {ACCION_VALIDA} Fin de respuesta."

        resultado = forzar_json(texto)

        self.assertIsInstance(resultado, dict)
        self.assertEqual(resultado["herramienta"], "write_file")

    def test_batch_de_acciones(self):
        texto = (
            '{"acciones":['
            '{"herramienta":"write_file",'
            '"argumentos":{"ruta":"a.py","contenido":"print(1)"}}'
            '],"respuesta":"ok"}'
        )

        resultado = forzar_json(texto)

        self.assertIsInstance(resultado, dict)
        self.assertEqual(len(resultado["acciones"]), 1)
        self.assertEqual(
            resultado["acciones"][0]["herramienta"],
            "write_file",
        )

    def test_json_sin_estructura_de_accion_devuelve_none(self):
        resultado = forzar_json('{"respuesta":"ok"}')

        self.assertIsNone(resultado)

    def test_texto_sin_json_devuelve_none(self):
        resultado = forzar_json("Esto es prosa normal sin JSON.")

        self.assertIsNone(resultado)

    def test_json_invalido_devuelve_none(self):
        resultado = forzar_json(
            '{"herramienta":"write_file","argumentos":'
        )

        self.assertIsNone(resultado)

    def test_llaves_dentro_de_string_no_rompen_el_balanceo(self):
        texto = (
            '{"herramienta":"write_file",'
            '"argumentos":{"ruta":"a.py",'
            '"contenido":"datos = {\\"clave\\": \\"valor\\"}\\n"},'
            '"resumen":"crear"}'
        )

        resultado = forzar_json(texto)

        self.assertIsInstance(resultado, dict)
        self.assertEqual(resultado["herramienta"], "write_file")


if __name__ == "__main__":
    unittest.main()
