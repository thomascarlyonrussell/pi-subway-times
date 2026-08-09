"""Unit tests for display color clamping and pixel width text truncation."""

import ast
import pathlib
import unittest

from subway_sign.display import (
    clamp_color_value,
    get_char_width,
    get_clamped_color,
    get_string_width,
    truncate_to_pixel_width,
)


class MockFont:
    """Mock font mimicking Adobe Helvetica 8pt BDF character widths."""

    def __init__(self, custom_widths=None):
        # Helvetica 8pt proportional character widths (DWIDTH x)
        self._widths = {
            "A": 6, "B": 6, "C": 6, "D": 6, "E": 6, "F": 5, "G": 6, "H": 6,
            "I": 2, "J": 4, "K": 6, "L": 5, "M": 7, "N": 6, "O": 6, "P": 6,
            "Q": 6, "R": 6, "S": 6, "T": 5, "U": 6, "V": 6, "W": 7, "X": 6,
            "Y": 6, "Z": 5, " ": 2, "-": 3, ".": 2, "0": 6, "1": 6, "2": 6,
            "3": 6, "4": 6, "5": 6, "6": 6, "7": 6, "8": 6, "9": 6,
        }
        if custom_widths:
            self._widths.update(custom_widths)

    def CharacterWidth(self, char_code):
        char = chr(char_code)
        return self._widths.get(char, 6)


class DisplayValidation(unittest.TestCase):
    def setUp(self):
        self.font = MockFont()

    def test_clamp_color_value(self):
        self.assertEqual(clamp_color_value(-10), 0)
        self.assertEqual(clamp_color_value(128), 128)
        self.assertEqual(clamp_color_value(300), 255)

    def test_get_clamped_color(self):
        color = get_clamped_color(0xFF8000)
        # On non-Pi environments without rgbmatrix, returns tuple (r, g, b) or RGBMatrix Color object
        if isinstance(color, tuple):
            self.assertEqual(color, (255, 128, 0))

    def test_get_char_width_mock_and_fallback(self):
        self.assertEqual(get_char_width(self.font, "I"), 2)
        self.assertEqual(get_char_width(self.font, "W"), 7)
        self.assertEqual(get_char_width(self.font, " "), 2)
        # Fallback when font is None or lacks CharacterWidth
        self.assertEqual(get_char_width(None, "W"), 6)

    def test_get_string_width(self):
        # 'I' (2) + 'I' (2) + 'I' (2) = 6
        self.assertEqual(get_string_width(self.font, "III"), 6)
        # 'W' (7) + 'A' (6) + 'S' (6) + 'H' (6) = 25
        self.assertEqual(get_string_width(self.font, "WASH"), 25)
        self.assertEqual(get_string_width(self.font, ""), 0)

    def test_truncate_to_pixel_width_wide_station_names(self):
        # "WASHINGTON SQ": W(7)+A(6)+S(6)+H(6)+I(2)+N(6)+G(6)+T(5)+O(6)+N(6)+ (2)+S(6)+Q(6) = 71px
        truncated = truncate_to_pixel_width(self.font, "WASHINGTON SQ", max_pixels=42)
        width = get_string_width(self.font, truncated)
        self.assertLessEqual(width, 42)
        # "WASHIN" = 7+6+6+6+2+6 = 33px. "WASHING" = 33+6 = 39px <= 42px. "WASHINGT" = 39+5 = 44px > 42px
        self.assertEqual(truncated, "WASHING")

    def test_truncate_to_pixel_width_narrow_vs_wide_characters(self):
        # "III III III III" -> narrow chars ('I'=2, ' '=2)
        # "III III III III" = 12*'I' (24) + 3*' ' (6) = 30px <= 42px -> no truncation needed
        narrow_text = "III III III III"
        truncated_narrow = truncate_to_pixel_width(self.font, narrow_text, max_pixels=42)
        self.assertEqual(truncated_narrow, narrow_text)
        self.assertLessEqual(get_string_width(self.font, truncated_narrow), 42)

        # "WWW WWW WWW WWW" -> wide chars ('W'=7, ' '=2)
        # "WWW WWW" = 6*'W' (42) + 1*' ' (2) = 44px > 42px
        wide_text = "WWW WWW WWW WWW"
        truncated_wide = truncate_to_pixel_width(self.font, wide_text, max_pixels=42)
        self.assertLessEqual(get_string_width(self.font, truncated_wide), 42)
        self.assertNotEqual(truncated_wide, wide_text)

    def test_truncate_to_pixel_width_respects_max_chars(self):
        # Even if pixel width allows 10 chars, max_chars=5 caps it to 5 chars
        text = "III III III III"
        truncated = truncate_to_pixel_width(self.font, text, max_pixels=42, max_chars=5)
        self.assertEqual(truncated, "III I")
        self.assertEqual(len(truncated), 5)

    def test_truncate_to_pixel_width_edge_cases(self):
        self.assertEqual(truncate_to_pixel_width(self.font, "", max_pixels=42), "")
        self.assertEqual(truncate_to_pixel_width(self.font, None, max_pixels=42), "")
        self.assertEqual(truncate_to_pixel_width(self.font, "TEST", max_pixels=0), "TEST")
        self.assertEqual(truncate_to_pixel_width(self.font, "TEST", max_pixels=-10), "TEST")

    def test_main_retains_canvas_returned_by_matrix_swap(self):
        main_path = pathlib.Path(__file__).resolve().parents[1] / "src" / "subway_sign" / "main.py"
        module = ast.parse(main_path.read_text(encoding="utf-8"))
        swaps = [
            statement
            for statement in ast.walk(module)
            if isinstance(statement, ast.Assign)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Attribute)
            and statement.value.func.attr == "SwapOnVSync"
        ]

        self.assertGreaterEqual(len(swaps), 2)
        self.assertTrue(
            all(any(isinstance(target, ast.Name) and target.id == "canvas" for target in swap.targets) for swap in swaps)
        )

    def test_main_renders_starting_status_before_loading_gtfs_indexes(self):
        main_path = pathlib.Path(__file__).resolve().parents[1] / "src" / "subway_sign" / "main.py"
        source = main_path.read_text(encoding="utf-8")

        self.assertLess(source.index('"STARTING..."'), source.index("trips = Trips("))
        self.assertIn("Display startup: STARTING frame rendered", source)
        self.assertIn("Display startup: CONNECTING frame rendered; fetching MTA arrivals", source)


if __name__ == "__main__":
    unittest.main()
