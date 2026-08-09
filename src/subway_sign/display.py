try:
    from rgbmatrix import graphics
except ImportError:  # pragma: no cover - absent on non-Pi desktop environment
    graphics = None


def clamp_color_value(value):
    return max(0, min(value, 255))


def get_clamped_color(color_value):
    r = clamp_color_value((color_value >> 16) & 0xFF)
    g = clamp_color_value((color_value >> 8) & 0xFF)
    b = clamp_color_value(color_value & 0xFF)
    if graphics is not None:
        return graphics.Color(r, g, b)
    return (r, g, b)


def get_char_width(font, char):
    if font is not None and hasattr(font, "CharacterWidth"):
        try:
            w = font.CharacterWidth(ord(char))
            if w > 0:
                return w
        except Exception:
            pass
    return 6


def get_string_width(font, text):
    if not text:
        return 0
    return sum(get_char_width(font, char) for char in text)


def truncate_to_pixel_width(font, text, max_pixels=40, max_chars=None):
    if not text:
        return ""
    if max_chars is not None and max_chars > 0 and len(text) > max_chars:
        text = str(text)[:max_chars]
    else:
        text = str(text)
    if max_pixels is None or max_pixels <= 0:
        return text

    current_width = 0
    result = []
    for char in text:
        char_w = get_char_width(font, char)
        if current_width + char_w > max_pixels:
            break
        current_width += char_w
        result.append(char)

    return "".join(result)
