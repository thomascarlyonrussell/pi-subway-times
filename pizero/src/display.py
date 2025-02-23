from rgbmatrix import graphics

def clamp_color_value(value):
    return max(0, min(value, 255))

def get_clamped_color(color_value):
    return graphics.Color(clamp_color_value((color_value >> 16) & 0xFF),
                          clamp_color_value((color_value >> 8) & 0xFF),
                          clamp_color_value(color_value & 0xFF))