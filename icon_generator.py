from PIL import Image, ImageDraw
from pathlib import Path
import os
import struct


def _write_ico(im: Image.Image, path: str):
    width, height = im.size
    if width != height or width > 256:
        im = im.resize((256, 256), Image.LANCZOS)
        width, height = 256, 256

    png_data = im.tobytes("raw", "BGRA")
    png_size = len(png_data)

    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, 1))
        f.write(struct.pack("<BBBBHHII",
                            width % 256 or 0,
                            height % 256 or 0,
                            0,
                            0,
                            1,
                            32,
                            png_size,
                            22))
        f.write(png_data)


def generate_icon(output_path: str = None, size: int = 256) -> str:
    base_dir = Path(__file__).parent
    png_path = str(base_dir / "app_icon.png")
    ico_path = str(base_dir / "app_icon.ico")
    icon_path = output_path or png_path

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_size = size
    r = int(size * 0.2)
    draw.rounded_rectangle(
        [(0, 0), (bg_size - 1, bg_size - 1)],
        radius=r,
        fill=(42, 157, 255, 255),
    )

    cx, cy = size // 2, size // 2
    margin = int(size * 0.22)
    left_x = int(size * 0.15)
    right_x = int(size * 0.85)

    dot_radius = int(size * 0.08)
    draw.ellipse(
        [
            (left_x - dot_radius, cy - dot_radius),
            (left_x + dot_radius, cy + dot_radius),
        ],
        fill=(255, 255, 255, 255),
    )
    draw.ellipse(
        [
            (right_x - dot_radius, cy - dot_radius),
            (right_x + dot_radius, cy + dot_radius),
        ],
        fill=(255, 255, 255, 255),
    )

    line_width = int(size * 0.04)
    top_y = int(size * 0.30)
    bottom_y = int(size * 0.70)
    center_x = cx

    draw.line(
        [(left_x, cy), (center_x, top_y)],
        fill=(255, 255, 255, 255),
        width=line_width,
    )
    draw.line(
        [(right_x, cy), (center_x, top_y)],
        fill=(255, 255, 255, 255),
        width=line_width,
    )
    draw.line(
        [(center_x, top_y), (center_x, bottom_y)],
        fill=(255, 255, 255, 255),
        width=line_width,
    )

    small_size = int(size * 0.16)
    small_path = str(base_dir / "app_icon_small.png")
    small_img = img.resize((small_size, small_size), Image.LANCZOS)
    small_img.save(small_path, "PNG")

    img.save(png_path, "PNG")
    _write_ico(img, ico_path)

    return icon_path


if __name__ == "__main__":
    generate_icon()
    print("Icons generated successfully.")
