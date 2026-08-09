import logging
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from subway_sign.route_symbols import (
    DEFAULT_ROUTE_SYMBOL_ALIASES,
    ImageRouteSymbolBackend,
    RouteSymbolRenderer,
    TextRouteSymbolBackend,
    _normalize_route_id,
)

try:
    from PIL import Image
except ImportError:
    Image = None


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class MockCanvas:
    def __init__(self):
        self.pixels = {}

    def SetPixel(self, x, y, r, g, b):
        self.pixels[(x, y)] = (r, g, b)


class MockFont:
    pass


class RouteSymbolsValidation(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("validate_route_symbols")
        self.assets_dir = REPO_ROOT / "assets" / "route_symbols"

    @unittest.skipIf(Image is None, "Pillow not installed")
    def test_image_backend_preserves_multicolor_glyph_and_bullet_colors(self):
        backend = ImageRouteSymbolBackend(
            assets_dir=self.assets_dir,
            max_asset_px=10,
            cache_limit=10,
            route_symbol_aliases=DEFAULT_ROUTE_SYMBOL_ALIASES,
            logger=self.logger,
        )
        self.assertTrue(backend.can_render("F"))

        canvas = MockCanvas()
        # Call render for route "F" (route_color passed as orange 0xFF6319)
        backend.render(canvas, "F", x=0, baseline_y=9, color_value=0xFF6319)

        # F symbol top y is baseline_y - 10 + 1 = 0
        # Check that we drew pixels
        self.assertGreater(len(canvas.pixels), 0)

        # Check white glyph pixels inside F cutout (e.g. around center pixels (3,3) or (4,2))
        # Orange background pixels should have high R and moderate G/low B.
        # White F glyph pixels should have high R AND high G AND high B (>150).
        white_glyph_pixels = [
            color for pos, color in canvas.pixels.items() if color[0] > 200 and color[1] > 180 and color[2] > 150
        ]
        self.assertGreater(
            len(white_glyph_pixels),
            0,
            "F symbol must contain white/light glyph pixels rather than solid orange",
        )

        orange_bullet_pixels = [
            color for pos, color in canvas.pixels.items() if color[0] > 200 and 60 <= color[1] <= 130 and color[2] < 50
        ]
        self.assertGreater(
            len(orange_bullet_pixels),
            0,
            "F symbol must contain orange bullet background pixels",
        )

    @unittest.skipIf(Image is None, "Pillow not installed")
    def test_image_backend_renders_transparent_cutout_for_n_train(self):
        backend = ImageRouteSymbolBackend(
            assets_dir=self.assets_dir,
            max_asset_px=10,
            cache_limit=10,
            route_symbol_aliases=DEFAULT_ROUTE_SYMBOL_ALIASES,
            logger=self.logger,
        )
        self.assertTrue(backend.can_render("N"))

        canvas = MockCanvas()
        backend.render(canvas, "N", x=0, baseline_y=9, color_value=0xFCCC0A)

        # N symbol has yellow bullet background and transparent N glyph cutout
        self.assertNotIn((3, 2), canvas.pixels, "N symbol cutout pixel at (3,2) should be transparent/omitted")
        yellow_pixels = [
            color for pos, color in canvas.pixels.items() if color[0] > 200 and color[1] > 150
        ]
        self.assertGreater(len(yellow_pixels), 0, "N symbol must contain yellow bullet background pixels")

    @unittest.skipIf(Image is None, "Pillow not installed")
    def test_image_backend_renders_black_glyph_for_w_train(self):
        backend = ImageRouteSymbolBackend(
            assets_dir=self.assets_dir,
            max_asset_px=10,
            cache_limit=10,
            route_symbol_aliases=DEFAULT_ROUTE_SYMBOL_ALIASES,
            logger=self.logger,
        )
        self.assertTrue(backend.can_render("W"))

        canvas = MockCanvas()
        backend.render(canvas, "W", x=0, baseline_y=9, color_value=0xFCCC0A)

        black_glyph_pixels = [
            color for pos, color in canvas.pixels.items() if color[0] < 60 and color[1] < 60 and color[2] < 60
        ]
        self.assertGreater(
            len(black_glyph_pixels),
            0,
            "W symbol must contain dark/black glyph pixels",
        )

    @unittest.skipIf(Image is None, "Pillow not installed")
    def test_image_backend_alpha_transparency_excludes_corners(self):
        backend = ImageRouteSymbolBackend(
            assets_dir=self.assets_dir,
            max_asset_px=10,
            cache_limit=10,
            route_symbol_aliases=DEFAULT_ROUTE_SYMBOL_ALIASES,
            logger=self.logger,
        )
        canvas = MockCanvas()
        backend.render(canvas, "F", x=0, baseline_y=9, color_value=0xFF6319)

        # Extreme 4 corners (0,0), (9,0), (0,9), (9,9) should be transparent and omitted
        for corner in [(0, 0), (9, 0), (0, 9), (9, 9)]:
            self.assertNotIn(
                corner,
                canvas.pixels,
                f"Corner pixel {corner} must be transparent/omitted",
            )

    @unittest.skipIf(Image is None, "Pillow not installed")
    def test_image_backend_resolves_aliases(self):
        backend = ImageRouteSymbolBackend(
            assets_dir=self.assets_dir,
            max_asset_px=10,
            cache_limit=10,
            route_symbol_aliases={"FX": "FD"},
            logger=self.logger,
        )
        self.assertTrue(backend.can_render("FX"))
        self.assertEqual(backend._resolve_symbol_key("FX"), "FD")

    def test_renderer_falls_back_to_text_when_image_is_unavailable(self):
        image_backend = mock.Mock(spec=ImageRouteSymbolBackend)
        image_backend.name = "image"
        image_backend.can_render.return_value = False
        text_backend = mock.Mock(spec=TextRouteSymbolBackend)
        text_backend.name = "text"
        text_backend.can_render.return_value = True

        renderer = RouteSymbolRenderer([image_backend, text_backend], logger=self.logger)
        used_backend = renderer.render(None, "F", x=0, baseline_y=9, color_value=0xFF6319)

        self.assertEqual(used_backend, "text")
        text_backend.render.assert_called_once_with(None, "F", 0, 9, 0xFF6319)


if __name__ == "__main__":
    unittest.main()
