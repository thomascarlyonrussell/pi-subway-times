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