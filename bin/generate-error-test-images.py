from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# Generates deterministic image-analysis test samples from the same clean
# product image used on the PDF cover. Only the pump screen is changed.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "aster-pump-aftercare-backend" / "docs" / "assets"
SOURCE_IMAGE = ASSETS_DIR / "asterpump_x17_cover.png"
OUTPUT_DIR = ASSETS_DIR / "test-images"


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a bold local font, falling back to Pillow's built-in font."""

    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/Arialbd.ttf"),
        Path("C:/Windows/Fonts/consolab.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def draw_error_code(source: Image.Image, code: str) -> Image.Image:
    """Return a copy of the source image with a clear error code on the screen."""

    image = source.convert("RGB").copy()
    draw = ImageDraw.Draw(image)

    # Coordinates are tuned for asterpump_x17_cover.png at 1055x1491.
    # They cover only the inner display, leaving the pump body unchanged.
    screen_box = (478, 667, 723, 969)
    screen_inner = (494, 688, 707, 947)

    draw.rounded_rectangle(screen_box, radius=28, fill=(8, 17, 24), outline=(24, 171, 190), width=5)
    draw.rounded_rectangle(screen_inner, radius=18, fill=(7, 19, 30), outline=(18, 62, 76), width=2)

    font = load_font(72)
    label_font = load_font(24)

    code_bbox = draw.textbbox((0, 0), code, font=font)
    code_width = code_bbox[2] - code_bbox[0]
    code_height = code_bbox[3] - code_bbox[1]
    code_x = screen_inner[0] + ((screen_inner[2] - screen_inner[0]) - code_width) / 2
    code_y = screen_inner[1] + 66

    # Blue glow plus white-blue foreground makes the code easy for humans and
    # simple OCR/object extraction services to detect.
    for offset in range(5, 0, -1):
        draw.text(
            (code_x - offset / 2, code_y - offset / 2),
            code,
            font=font,
            fill=(20, 112, 180),
        )
    draw.text((code_x, code_y), code, font=font, fill=(210, 240, 255))

    label = "SERVICE REQUIRED"
    label_bbox = draw.textbbox((0, 0), label, font=label_font)
    label_width = label_bbox[2] - label_bbox[0]
    label_x = screen_inner[0] + ((screen_inner[2] - screen_inner[0]) - label_width) / 2
    draw.text((label_x, code_y + code_height + 24), label, font=label_font, fill=(99, 220, 235))

    # Small status strip at the bottom keeps the display looking like a real UI.
    strip_y = screen_inner[3] - 42
    for index in range(8):
        x = screen_inner[0] + 38 + index * 18
        color = (64, 197, 218) if index < 5 else (31, 73, 88)
        draw.rounded_rectangle((x, strip_y, x + 11, strip_y + 24), radius=2, fill=color)

    return image


def main() -> None:
    """Create the three requested error-code image samples."""

    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(f"Missing source image: {SOURCE_IMAGE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE_IMAGE)

    for code in ("E-41", "E-77", "E-93"):
        output_path = OUTPUT_DIR / f"asterpump_x17_{code.lower().replace('-', '')}_screen.png"
        draw_error_code(source, code).save(output_path, format="PNG")
        print(output_path)


if __name__ == "__main__":
    main()
