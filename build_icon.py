from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size):
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


output = Path(__file__).parent / "assets" / "AttackSharkBatteryTray.ico"
output.parent.mkdir(parents=True, exist_ok=True)

canvas = Image.new("RGBA", (256, 256), (20, 28, 38, 255))
draw = ImageDraw.Draw(canvas)
draw.rounded_rectangle((12, 12, 243, 243), radius=52, outline=(49, 204, 113, 255), width=14)

font = load_font(110)
text = "AS"
left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
x = (256 - (right - left)) / 2 - left
y = (256 - (bottom - top)) / 2 - top - 4
draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

canvas.save(output, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
canvas.save(output.with_suffix(".png"), format="PNG")
print(output)
