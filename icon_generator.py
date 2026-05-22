from PIL import Image, ImageDraw
from pathlib import Path
import struct
import io


def _write_ico(im: Image.Image, path: str):
    """
    生成标准格式的 ICO 文件（使用 PNG 压缩存储）
    """
    width, height = im.size
    if width != height or width > 256:
        im = im.resize((256, 256), Image.LANCZOS)
        width, height = 256, 256

    # 使用 PNG 格式存储图标数据（体积小、兼容性好）
    png_buffer = io.BytesIO()
    im.save(png_buffer, format='PNG')
    png_data = png_buffer.getvalue()
    png_size = len(png_data)

    with open(path, "wb") as f:
        # ICO header
        f.write(struct.pack("<HHH", 0, 1, 1))
        # ICO directory entry
        f.write(struct.pack("<BBBBHHII",
                            width % 256 or 0,
                            height % 256 or 0,
                            0,  # color count (0 = 256+)
                            0,  # reserved
                            1,  # color planes
                            32, # bits per pixel
                            png_size,
                            22))  # offset to image data
        # PNG data
        f.write(png_data)


def generate_icon(output_path: str = None) -> str:
    """
    生成应用图标（PNG + ICO 格式）
    """
    size = 256
    base_dir = Path(__file__).parent
    png_path = str(base_dir / "app_icon.png")
    ico_path = str(base_dir / "app_icon.ico")

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 蓝色圆角背景
    bg_size = size
    r = int(size * 0.2)
    draw.rounded_rectangle(
        [(0, 0), (bg_size - 1, bg_size - 1)],
        radius=r,
        fill=(42, 157, 255, 255),
    )

    # 绘制网络图标图案
    cx, cy = size // 2, size // 2
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

    # 保存 PNG 和 ICO
    img.save(png_path, "PNG")
    _write_ico(img, ico_path)

    return ico_path


if __name__ == "__main__":
    path = generate_icon()
    print(f"Icons generated: {path}")
