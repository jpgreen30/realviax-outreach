#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os

out_dir = "/home/jpgreen1/.openclaw/workspace/realviax-outreach/assets"
os.makedirs(out_dir, exist_ok=True)

# Create a transparent logo image (width x height)
img = Image.new("RGBA", (400, 120), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Try to load a nice font; fall back to default
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
except Exception:
    font = ImageFont.load_default()

text = "REALVIAX"
text_color = (255, 255, 255, 255)  # white

# Get text bounding box and center
bbox = draw.textbbox((0,0), text, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]

x = (img.width - text_w) // 2
y = (img.height - text_h) // 2

draw.text((x, y), text, fill=text_color, font=font)

out_path = os.path.join(out_dir, "logo.png")
img.save(out_path)
print(f"Logo saved to {out_path}")
