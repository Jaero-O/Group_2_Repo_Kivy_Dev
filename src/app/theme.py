"""Centralized design tokens for colors and typography.

Screens import these tokens to reduce hardcoded styling and aid
visual regression alignment with Figma references.
"""

COLORS = {
    'bg_primary': (247/255, 249/255, 245/255, 1),  # light neutral green-ish
    'bg_secondary': (248/255, 248/255, 248/255, 1),  # light gray
    'bg_card': (1, 1, 1, 1),  # white
    'bg_card_selected': (232/255, 255/255, 208/255, 1),  # light green-yellow
    
    'text_primary': (56/255, 73/255, 38/255, 1),  # dark green
    'text_secondary': (99/255, 99/255, 99/255, 1),  # medium gray
    'text_dark': (3/255, 30/255, 0/255, 1),  # very dark green
    'text_light': (1, 1, 1, 1),  # white
    
    'accent': (220/255, 53/255, 69/255, 1),  # red
    'accent_secondary': (49/255, 49/255, 49/255, 1),  # dark gray
    
    'border': (0, 0, 0, 0.1),  # light transparent black
    'border_medium': (0, 0, 0, 0.15),  # medium transparent black
    'border_light': (220/255, 220/255, 220/255, 1),  # light gray
    
    'shadow': (0, 0, 0, 0.2),  # shadow overlay
    'overlay': (0.5, 0.5, 0.5, 0.3),  # touch feedback
    
    'error': (220/255, 53/255, 69/255, 1),  # red
    'warning': (0.5, 0, 0, 1),  # dark red
    'success': (0, 0.8, 0.2, 1),  # green
}

FONTS = {
    'heading_size': 24,
    'subheading_size': 18,
    'title_size': 32,
    'large_title_size': 34,
    'body_size': 15,
    'small_size': 13,
    'caption_size': 14,
}

SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 12,
    'lg': 20,
    'xl': 28,
}

RADIUS = {
    'sm': 8,
    'md': 11,
    'lg': 15,
    'xl': 18,
    'xxl': 40,
}

def apply_background(widget, color_key='bg_primary'):
    """Apply a background color to a root widget if graphics are available."""
    import os
    if os.environ.get('HEADLESS_TEST') == '1':
        # Skip graphics operations in headless test mode to avoid Window/provider errors.
        return
    try:
        from kivy.graphics import Color, Rectangle
        color = COLORS.get(color_key, (1,1,1,1))
        with widget.canvas.before:
            Color(*color)
            widget._bg_rect = Rectangle(pos=widget.pos, size=widget.size)
        def _update(_w, _val):
            try:
                widget._bg_rect.pos = widget.pos
                widget._bg_rect.size = widget.size
            except Exception:
                pass
        widget.bind(pos=_update, size=_update)
    except Exception:
        pass
