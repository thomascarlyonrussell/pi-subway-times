import importlib
import pathlib
import time
from typing import Optional


PHASE_LABELS = {
    "setup": "SETUP",
    "download": "DOWNLOAD",
    "unpack": "UNPACK",
    "stations": "STATIONS",
    "finalize": "FINALIZE",
    "ready": "READY",
    "failed": "FAILED",
}


class BootstrapStatusRenderer:
    def __init__(self, display_config: dict, project_root: Optional[pathlib.Path] = None):
        self.display_config = display_config
        self.project_root = project_root or pathlib.Path(__file__).resolve().parent.parent
        self.matrix = None
        self.canvas = None
        self.graphics = None
        self.font = None
        self.last_render_at = 0.0
        self.last_render_key = None

    def start(self) -> None:
        rgb_dir = self.project_root.parent / "rpi-rgb-led-matrix" / "bindings" / "python"
        import sys

        if str(rgb_dir) not in sys.path:
            sys.path.append(str(rgb_dir))
        rgbmatrix = importlib.import_module("rgbmatrix")
        RGBMatrix = rgbmatrix.RGBMatrix
        RGBMatrixOptions = rgbmatrix.RGBMatrixOptions
        graphics = rgbmatrix.graphics

        options = RGBMatrixOptions()
        options.rows = int(self.display_config["led_rows"])
        options.cols = int(self.display_config["led_columns"])
        options.chain_length = int(self.display_config["led_chain_length"])
        options.parallel = int(self.display_config["led_parallel"])
        options.hardware_mapping = self.display_config["led_hardware_mapping"]
        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.graphics = graphics
        self.font = graphics.Font()
        self.font.LoadFont(str(self.project_root / "fonts" / "10-Adobe-Helvetica.bdf"))

    def update(self, phase: str, completed: int = 0, total: int = 0, detail: str = "") -> None:
        if self.matrix is None:
            self.start()
        label = PHASE_LABELS.get(phase, "SETUP")
        detail_text = str(detail or "")[:10].upper()
        progress = 0 if total <= 0 else max(0, min(64, int((completed / float(total)) * 64)))
        render_key = (phase, detail_text, progress)
        now = time.monotonic()
        if render_key == self.last_render_key or (now - self.last_render_at) < 0.5:
            return
        color = self.graphics.Color(255, 255, 255)
        phase_color = self.graphics.Color(0, 200, 255) if phase != "failed" else self.graphics.Color(255, 64, 64)
        self.canvas.Clear()
        self.graphics.DrawText(self.canvas, self.font, 0, 10, phase_color, label[:10])
        if detail_text:
            self.graphics.DrawText(self.canvas, self.font, 0, 21, color, detail_text)
        if total > 0:
            self.graphics.DrawLine(self.canvas, 0, 31, progress, 31, phase_color)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        self.last_render_at = now
        self.last_render_key = render_key

    def close(self) -> None:
        self.canvas = None
        self.matrix = None
        self.last_render_key = None


class NullBootstrapStatusRenderer:
    def update(self, phase: str, completed: int = 0, total: int = 0, detail: str = "") -> None:
        return None

    def close(self) -> None:
        return None