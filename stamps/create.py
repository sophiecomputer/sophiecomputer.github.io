"""
Script for creating stamps.
"""

import argparse
import math 
import os
import textwrap 

from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from typing import Tuple


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", required=True, 
        help="Path to the background image (can be any size)")
    parser.add_argument("--text", required=True, 
        help="Text to put in the stamp (\\n = newline)") 
    parser.add_argument("--border", default="spiky",
        choices=["ridged", "rounded", "square", "spiky", "bubble"])
    parser.add_argument("--corner-text", default="")
    parser.add_argument("--border-color", default="white")
    parser.add_argument("--text-fill-color", default="white") 
    parser.add_argument("--text-border-color", default="black")
    parser.add_argument("--style", default="normal",
        choices=["normal", "italics", "bold", "italics-bold"])
    parser.add_argument("--no-serifs", action="store_true", default=False)
    parser.add_argument("--gray", action="store_true", default=False) 
    parser.add_argument("--effect", default=None, 
        choices=["shimmer", "pulse", "wave", "holographic"])
    return parser.parse_args()


def fit_text(draw, text, font_path, max_width, max_height,
             min_size=6, max_size=200):
    """
    Find the largest font size that allows the text to fit inside
    the specified rectangle.
    """
    best_font = None

    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size)

        bbox = draw.multiline_textbbox(
            (0, 0),
            text,
            font=font,
            align="center"
        )

        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if width <= max_width and height <= max_height:
            best_font = font
            break

    if best_font is None:
        best_font = ImageFont.truetype(font_path, min_size)
    else:
        # Size down the font a little further. 
        best_font = ImageFont.truetype(font_path, size) 
    
    return best_font


def unobtained_filter(image):
    """
    Apply a 'locked/unobtained' effect while preserving alpha.

    - Reduce saturation.
    - Pull colors toward grayscale.
    - Compress brightness toward middle gray so
      blacks become lighter and whites become darker.
    """

    image = image.convert("RGBA")

    pixels = list(image.get_flattened_data())
    new_pixels = []

    for r, g, b, a in pixels:

        if a == 0:
            new_pixels.append((r, g, b, a))
            continue

        # Perceptual grayscale.
        gray = int(0.299 * r + 0.587 * g + 0.114 * b)

        # Desaturate heavily (80%).
        saturation = 0.2

        r = int(gray + (r - gray) * saturation)
        g = int(gray + (g - gray) * saturation)
        b = int(gray + (b - gray) * saturation)

        # Compress toward middle gray (128).
        # Black (0) becomes 64.
        # White (255) becomes 191.
        compression = 0.5

        r = int(128 + (r - 128) * compression)
        g = int(128 + (g - 128) * compression)
        b = int(128 + (b - 128) * compression)

        new_pixels.append((r, g, b, a))

    result = Image.new("RGBA", image.size)
    result.putdata(new_pixels)
    return result


def special_effect(image, effect):
    """
    Applies a special effect to the image. 
    """

    assert effect in ("shimmer", "pulse", "wave", "holographic"), effect
    
    FPS = 10  # Don't change.
    DURATION = 5
    N_FRAMES = FPS * DURATION 

    image = image.convert("RGBA")

    w, h = image.size
    src = image.load()

    frames = []
    
    tint = (128, 0, 128)
    def tint_pixel(r, g, b, amount):
        ar, ag, ab = (
            amount if isinstance(amount, tuple) else
            (amount, amount, amount) 
        )
        tr, tg, tb = tint 
        lum = (r + g + b) / 100.0 
        target_r = lum * tr 
        target_g = lum * tg 
        target_b = lum * tb
        r = int(r + (target_r - r) * ar)
        g = int(g + (target_g - g) * ag)
        b = int(b + (target_b - b) * ab)
        return r, g, b

    if effect == "shimmer":
        for frame in range(N_FRAMES):
    
            t = frame / N_FRAMES
    
            sweep = -w + (3 * w) * t
    
            out = image.copy()
            dst = out.load()
    
            for y in range(h):
                for x in range(w):
    
                    r, g, b, a = src[x, y]
    
                    if a == 0:
                        continue
    
                    d = abs((x + y * 0.5) - sweep)
    
                    if d < 15:
                        strength = (1 - d / 15) * 0.25
                        
                        r, g, b = tint_pixel(r, g, b, strength)
    
                    dst[x, y] = (r, g, b, a)
    
            frames.append(out)
    elif effect == "pulse":  
        for frame in range(N_FRAMES):
            phase = 2 * math.pi * frame / N_FRAMES
    
            strength = 0.12 * (1 + math.sin(phase))
    
            out = image.copy()
            dst = out.load()
    
            for y in range(h):
                for x in range(w):
    
                    r, g, b, a = src[x, y]
    
                    if a == 0:
                        continue
    
                    r, g, b = tint_pixel(r, g, b, strength)
    
                    dst[x, y] = (r, g, b, a)
    
            frames.append(out)
    elif effect == "wave":
        for frame in range(N_FRAMES):
    
            t = frame / N_FRAMES
    
            out = image.copy()
            dst = out.load()
    
            for y in range(h):
                for x in range(w):
    
                    r, g, b, a = src[x, y]
    
                    if a == 0:
                        continue
    
                    wave = math.sin(
                        x / 8
                        + 2 * math.pi * t
                    )
    
                    strength = max(0, wave) * 0.12
    
                    r, g, b = tint_pixel(r, g, b, strength)
    
                    dst[x, y] = (r, g, b, a)
    
            frames.append(out)
    elif effect == "holographic":
        for frame in range(N_FRAMES):
    
            t = frame / N_FRAMES
    
            out = image.copy()
            dst = out.load()
    
            for y in range(h):
                for x in range(w):
    
                    r, g, b, a = src[x, y]
    
                    if a == 0:
                        continue
    
                    phase = (
                        x / 12
                        + y / 20
                        + 2 * math.pi * t
                    )
    
                    rr = 0.06 * (1 + math.sin(phase))
                    gg = 0.06 * (1 + math.sin(phase + 2.09))
                    bb = 0.06 * (1 + math.sin(phase + 4.18))
    
                    r, g, b = tint_pixel(r, g, b, (rr, gg, bb))
    
                    dst[x, y] = (r, g, b, a)
    
            frames.append(out)
    
    return frames


def create_stamp(
    background_path: str, 
    text: str, 
    border_type: str = "",
    corner_text: str = "",
    border_color: str = "white", 
    text_fill_color: Tuple[int] = "cyan",
    text_border_color: Tuple[int] = "black",
    style: str = "normal", 
    serifs: bool = True,
    gray: bool = False, 
    effect: str = None 
) -> str:
    """
    Creates a stamp image and returns the file name. 
    """

    assert style in ("normal", "italics", "bold", "italics-bold"), style
    assert effect in (
        None, "none", "shimmer", "pulse", "wave", "holographic"
    ), effect
    font_name = (
        (
            "times" if style == "normal" else 
            "timesbd" if style == "bold" else 
            "timesi" if style == "italics" else 
            "timesbi" if style == "italics-bold" else
            None 
        )
        if serifs else 
        (
            "OpenSans-Regular" if style == "normal" else 
            "OpenSans-SemiBold" if style == "bold" else 
            "OpenSans-Italic" if style == "italics" else 
            "OpenSans-SemiBoldItalic" if style == "italics-bold" else 
            None 
        )
    )
    font = f"/usr/share/fonts/TTF/{font_name}.ttf"
    assert os.path.exists(font), font
    corner_font = f"/usr/share/fonts/TTF/OpenSans-Regular.ttf"
    assert os.path.exists(corner_font), corner_font

    basedir = os.path.dirname(__file__)
    text = text.replace("\\n", "\n")

    # Load border.
    border_path = f"{basedir}/templates/border_{border_type}.png"
    assert os.path.exists(border_path), border_path
    border = Image.open(border_path).convert("RGBA") 
    assert border.size == (100, 65), repr(border.size)
    width, height = 100, 65

    # Extract the mask pixels from the border (which is any color that's not 
    # white).
    border_pixels = border.load()
    mask = [
        [
            (
                border_pixels[x, y][:3] != (255, 255, 255) and  # Not white  
                border_pixels[x, y][3] == 255  # Fully opaque
            )
            for x in range(width)
        ] for y in range(height)
    ]
    assert sum(1 for row in mask for cell in row if cell) > 0 

    # Adjust the border to be a different color.
    _, _, _, border_alpha = border.split() 
    border = Image.new("RGBA", border.size, border_color)
    border.putalpha(border_alpha)

    # Load and resize background. 
    assert os.path.exists(background_path), background_path 
    background = Image.open(background_path).convert("RGBA")
    image = background.resize((width, height), Image.Resampling.NEAREST)

    # Create image. 
    draw = ImageDraw.Draw(image)

    font = fit_text(
        draw,
        text,
        font,
        max_width=80,
        max_height=40,
        min_size=4,
        max_size=min(width, height)
    )

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        align="center"
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (width - text_width) / 2 - bbox[0]
    y = (height - text_height) / 2 - bbox[1]

    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=text_fill_color,
        spacing=0,
        stroke_width=2, 
        stroke_fill=text_border_color,
        align="center"
    )
    draw.text(
        (7, 4), 
        corner_text,
        font=ImageFont.truetype(corner_font, 12), 
        fill=border_color,
        stroke_width=2, 
        stroke_fill="black", 
        align="left"
    )

    # The "image" is the background with text on it. The "border" is a border
    # image with a white section on it around the edges, optionally transparent
    # pixels further out from the edges, and *non-white non-transparent pixels*
    # filling the center. The "image" will replace these center pixels. This is 
    # computed using the mask from earlier. 
    border_pixels = border.load()
    image_pixels = image.load() 
    result = Image.new("RGBA", border.size) 
    result_pixels = result.load() 
    for y in range(height):
        for x in range(width):
            if mask[y][x]:
                result_pixels[x, y] = image_pixels[x, y]
            else:
                result_pixels[x, y] = border_pixels[x, y]
    image = result

    # Optionally gray out the image or apply special effect. 
    save_function = lambda img, path: img.save(path)
    file_type = "png"
    if gray: 
        image = unobtained_filter(image)
    elif effect not in (None, "none"):
        image = special_effect(result, effect)
        file_type = "gif"
        save_function = lambda frames, path: frames[0].save(
            path, 
            save_all=True, 
            append_images=frames[1:], 
            duration=100,  # 10 FPS
            loop=0, 
        )

    downloads_path = Path.home() / "Downloads"
    if not os.path.exists(downloads_path):
        downloads_path = Path.home() / "downloads"
        if not os.path.exists(downloads_path):
            downloads_path = basedir
    downloads_path = str(downloads_path)

    output_path = os.path.abspath(f"{downloads_path}/stamp.{file_type}")
    save_function(image, output_path)  
    print(f"Image outputted to \"{output_path}\"")
    return output_path


if __name__ == "__main__":
    args = get_args()
    create_stamp(
        background_path=args.background,
        text=args.text, 
        border_type=args.border, 
        corner_text=args.corner_text,
        border_color=args.border_color,
        text_fill_color=args.text_fill_color, 
        text_border_color=args.text_border_color, 
        style=args.style, 
        serifs=(not args.no_serifs), 
        gray=args.gray,
        effect=args.effect
    )
