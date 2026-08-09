import argparse
import importlib
import logging
import os
import pathlib
import signal
import sys
import time
from typing import Optional

from subway_sign.config import load_runtime_config


class BootSplashRenderer:
    def __init__(self, display_config: Optional[dict] = None, project_root: Optional[pathlib.Path] = None):
        if display_config is None:
            try:
                display_config = load_runtime_config().get("display", {})
            except Exception:
                display_config = {}

        self.display_config = display_config or {}
        self.project_root = project_root or pathlib.Path(__file__).resolve().parents[2]
        self.matrix = None
        self.canvas = None
        self.graphics = None
        self.font = None
        self.running = False

    def start(self) -> None:
        rgb_dir = self.project_root.parent / "rpi-rgb-led-matrix" / "bindings" / "python"
        if str(rgb_dir) not in sys.path:
            sys.path.append(str(rgb_dir))

        rgbmatrix = importlib.import_module("rgbmatrix")
        RGBMatrix = rgbmatrix.RGBMatrix
        RGBMatrixOptions = rgbmatrix.RGBMatrixOptions
        graphics = getattr(rgbmatrix, "graphics", None)
        if graphics is None:
            graphics = importlib.import_module("rgbmatrix.graphics")

        self.graphics = graphics
        self.font = graphics.Font()
        font_path = self.project_root / "fonts" / "10-Adobe-Helvetica.bdf"
        if not font_path.exists():
            raise FileNotFoundError(f"Splash font not found at {font_path}")
        self.font.LoadFont(str(font_path))

        options = RGBMatrixOptions()
        options.rows = int(self.display_config.get("led_rows", 32))
        options.cols = int(self.display_config.get("led_columns", 64))
        options.chain_length = int(self.display_config.get("led_chain_length", 1))
        options.parallel = int(self.display_config.get("led_parallel", 1))
        options.hardware_mapping = self.display_config.get("led_hardware_mapping", "adafruit-hat")
        gpio_slowdown = int(
            self.display_config.get("led_gpio_slowdown", self.display_config.get("led_pwm_slowdown", 2))
        )
        if hasattr(options, "gpio_slowdown"):
            options.gpio_slowdown = gpio_slowdown
        if hasattr(options, "brightness"):
            options.brightness = int(self.display_config.get("brightness", 100))
        options.drop_privileges = False

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.running = True

    def render_frame(self, frame_count: int) -> None:
        if self.matrix is None or self.graphics is None:
            return

        cols = int(self.display_config.get("led_columns", 64))
        self.canvas.Clear()

        # Colors
        header_color = self.graphics.Color(0, 200, 255)  # Bright Cyan
        status_color = self.graphics.Color(255, 255, 255)  # White
        train_color = self.graphics.Color(255, 204, 0)  # MTA Gold / Yellow
        headlight_color = self.graphics.Color(255, 255, 200)  # Bright headlight

        # Headers
        self.graphics.DrawText(self.canvas, self.font, 0, 10, header_color, "MTA SUBWAY")
        self.graphics.DrawText(self.canvas, self.font, 0, 21, status_color, "BOOTING...")

        # Bottom row animated train/dot indicator (y = 31)
        # Train length is 6 pixels. Position loops smoothly across cols
        train_len = 6
        pos = (frame_count * 2) % cols

        for i in range(train_len):
            pixel_x = (pos + i) % cols
            c = headlight_color if i == train_len - 1 else train_color
            self.graphics.DrawLine(self.canvas, pixel_x, 31, pixel_x, 31, c)

        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def run_loop(self, duration: Optional[float] = None, fps: float = 12.0) -> None:
        if not self.running and self.matrix is None:
            self.start()

        self.running = True
        frame_delay = 1.0 / max(1.0, fps)
        start_time = time.monotonic()
        frame_count = 0

        while self.running:
            self.render_frame(frame_count)
            frame_count += 1

            if duration is not None and (time.monotonic() - start_time) >= duration:
                break

            time.sleep(frame_delay)

    def stop(self) -> None:
        self.running = False
        if self.canvas is not None and self.matrix is not None:
            try:
                self.canvas.Clear()
                self.canvas = self.matrix.SwapOnVSync(self.canvas)
            except Exception:
                pass
        self.canvas = None
        self.matrix = None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Early boot splash screen for MTA Subway LED matrix sign.")
    parser.add_argument("--duration", type=float, default=None, help="Optional duration in seconds to run before exiting.")
    parser.add_argument("--fps", type=float, default=12.0, help="Animation frame rate (frames per second).")
    args = parser.parse_args()

    renderer = BootSplashRenderer()

    def handle_signal(signum, frame):
        logging.info("Received signal %s, stopping boot splash...", signum)
        renderer.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        renderer.start()
        renderer.run_loop(duration=args.duration, fps=args.fps)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logging.error("Boot splash failed: %s", exc, exc_info=True)
        return 1
    finally:
        renderer.stop()


if __name__ == "__main__":
    sys.exit(main())
