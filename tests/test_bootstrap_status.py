import pathlib
import sys
import types
import unittest
from unittest import mock

from subway_sign.bootstrap_status import BootstrapStatusRenderer


class FakeCanvas:
    def __init__(self):
        self.clear_count = 0

    def Clear(self):
        self.clear_count += 1


class FakeMatrix:
    def __init__(self, options):
        self.options = options
        self.canvas = FakeCanvas()
        self.swap_count = 0

    def CreateFrameCanvas(self):
        return self.canvas

    def SwapOnVSync(self, canvas):
        self.swap_count += 1
        return canvas


class FakeFont:
    def LoadFont(self, path):
        self.path = path


class FakeGraphics:
    draw_calls = []
    line_calls = []

    @staticmethod
    def Color(red, green, blue):
        return (red, green, blue)

    @staticmethod
    def DrawText(canvas, font, x, y, color, text):
        FakeGraphics.draw_calls.append(text)

    @staticmethod
    def DrawLine(canvas, x1, y1, x2, y2, color):
        FakeGraphics.line_calls.append((x1, y1, x2, y2))


FakeGraphics.Font = FakeFont


class FakeOptions:
    pass


class BootstrapStatusValidation(unittest.TestCase):
    def setUp(self):
        FakeGraphics.draw_calls.clear()
        FakeGraphics.line_calls.clear()
        self.config = {
            "led_rows": 32,
            "led_columns": 64,
            "led_chain_length": 1,
            "led_parallel": 1,
            "led_hardware_mapping": "adafruit-hat",
        }

    def test_status_renders_phase_progress_and_releases_matrix(self):
        fake_module = types.SimpleNamespace(
            RGBMatrix=FakeMatrix,
            RGBMatrixOptions=FakeOptions,
            graphics=FakeGraphics,
        )
        with mock.patch.dict(sys.modules, {"rgbmatrix": fake_module}):
            renderer = BootstrapStatusRenderer(self.config)
            with mock.patch("subway_sign.bootstrap_status.time.monotonic", side_effect=[1.0, 2.0, 3.0]):
                renderer.update("download", completed=32, total=64, detail="base")
                renderer.update("finalize", detail="checks")
                renderer.update("failed", detail="terminal")

            self.assertIn("DOWNLOAD", FakeGraphics.draw_calls)
            self.assertIn("FINALIZE", FakeGraphics.draw_calls)
            self.assertIn("FAILED", FakeGraphics.draw_calls)
            self.assertIn((0, 31, 32, 31), FakeGraphics.line_calls)
            matrix = renderer.matrix
            renderer.close()
            self.assertIsNone(renderer.matrix)
            self.assertIsNone(renderer.canvas)
            self.assertEqual(matrix.swap_count, 4)

    def test_status_updates_are_throttled(self):
        fake_module = types.SimpleNamespace(
            RGBMatrix=FakeMatrix,
            RGBMatrixOptions=FakeOptions,
            graphics=FakeGraphics,
        )
        with mock.patch.dict(sys.modules, {"rgbmatrix": fake_module}):
            renderer = BootstrapStatusRenderer(self.config)
            with mock.patch("subway_sign.bootstrap_status.time.monotonic", side_effect=[1.0, 1.1, 1.2]):
                renderer.update("stations", completed=1, detail="base")
                renderer.update("stations", completed=2, detail="base")
                renderer.update("stations", completed=3, detail="base")
            self.assertEqual(renderer.matrix.swap_count, 1)


if __name__ == "__main__":
    unittest.main()
