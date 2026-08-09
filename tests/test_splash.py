import pathlib
import sys
import types
import unittest
from unittest import mock

from subway_sign.splash import BootSplashRenderer


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
        FakeGraphics.draw_calls.append((x, y, text))

    @staticmethod
    def DrawLine(canvas, x1, y1, x2, y2, color):
        FakeGraphics.line_calls.append((x1, y1, x2, y2, color))


FakeGraphics.Font = FakeFont


class FakeOptions:
    pass


class BootSplashValidation(unittest.TestCase):
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

    def test_splash_renders_header_status_and_train_lines(self):
        fake_module = types.SimpleNamespace(
            RGBMatrix=FakeMatrix,
            RGBMatrixOptions=FakeOptions,
            graphics=FakeGraphics,
        )
        with mock.patch.dict(sys.modules, {"rgbmatrix": fake_module}):
            renderer = BootSplashRenderer(self.config)
            renderer.start()
            renderer.render_frame(0)

            texts = [call[2] for call in FakeGraphics.draw_calls]
            self.assertIn("MTA SUBWAY", texts)
            self.assertIn("BOOTING...", texts)

            line_ys = [line[1] for line in FakeGraphics.line_calls]
            self.assertTrue(all(y == 31 for y in line_ys))
            self.assertGreater(len(FakeGraphics.line_calls), 0)

            renderer.stop()
            self.assertIsNone(renderer.matrix)
            self.assertIsNone(renderer.canvas)

    def test_splash_run_loop_terminates_after_duration(self):
        fake_module = types.SimpleNamespace(
            RGBMatrix=FakeMatrix,
            RGBMatrixOptions=FakeOptions,
            graphics=FakeGraphics,
        )
        with mock.patch.dict(sys.modules, {"rgbmatrix": fake_module}):
            renderer = BootSplashRenderer(self.config)
            renderer.run_loop(duration=0.05, fps=50.0)
            self.assertEqual(renderer.running, True)
            renderer.stop()
            self.assertIsNone(renderer.matrix)

    def test_systemd_services_stop_splash_before_taking_the_matrix(self):
        unit_path = pathlib.Path(__file__).resolve().parents[1] / "setup" / "subway-splash.service"
        setup_script_path = unit_path.parent / "setup_subway_sign.sh"

        unit_text = unit_path.read_text()
        setup_script_text = setup_script_path.read_text()
        self.assertIn("ExecStart=/home/subwaysign/project/.venv/bin/subway-splash", unit_text)
        self.assertNotIn("--duration", unit_text)
        self.assertNotIn("Conflicts=", unit_text)
        self.assertNotIn("Conflicts=", setup_script_text)
        self.assertEqual(setup_script_text.count("ExecStartPre=/usr/bin/systemctl stop subway-splash.service"), 2)


if __name__ == "__main__":
    unittest.main()
