from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import base64
import io
import os
import urllib.request

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

FONT_URLS = {
    "NotoSansBengali-Regular.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Regular.ttf",
    "NotoSansBengali-Bold.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Bold.ttf",
    "MuktaBangla-Regular.ttf": "https://github.com/googlefonts/mukta-fonts/raw/master/fonts/ttf/MuktaBangla-Regular.ttf",
    "MuktaBangla-Bold.ttf": "https://github.com/googlefonts/mukta-fonts/raw/master/fonts/ttf/MuktaBangla-Bold.ttf",
    "MuktaBangla-ExtraBold.ttf": "https://github.com/googlefonts/mukta-fonts/raw/master/fonts/ttf/MuktaBangla-ExtraBold.ttf",
    "MuktaBangla-Light.ttf": "https://github.com/googlefonts/mukta-fonts/raw/master/fonts/ttf/MuktaBangla-Light.ttf",
}

def download_fonts():
    for fname, url in FONT_URLS.items():
        fpath = os.path.join(FONT_DIR, fname)
        if not os.path.exists(fpath):
            try:
                print(f"Downloading {fname}...")
                urllib.request.urlretrieve(url, fpath)
                print(f"OK: {fname}")
            except Exception as e:
                print(f"Failed {fname}: {e}")

download_fonts()

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    try:
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return (r, g, b, int(alpha))
    except:
        return (255,255,255,int(alpha))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/fonts")
def list_fonts():
    fonts = [f for f in os.listdir(FONT_DIR) if f.endswith((".ttf",".otf"))]
    return jsonify(sorted(fonts))

@app.route("/render", methods=["POST"])
def render_text():
    try:
        data = request.json
        image_data = data.get("image")
        texts = data.get("texts", [])
        width = int(data.get("width", 800))
        height = int(data.get("height", 600))

        if image_data and "," in image_data:
            img_bytes = base64.b64decode(image_data.split(",")[1])
            img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            img = img.resize((width, height), Image.LANCZOS)
        else:
            img = Image.new("RGBA", (width, height), (20, 20, 30, 255))

        composite = img.copy()

        for obj in texts:
            text = obj.get("text", "")
            if not text:
                continue

            x = int(obj.get("x", 100))
            y = int(obj.get("y", 100))
            font_size = max(10, int(obj.get("fontSize", 60)))
            color = obj.get("color", "#ffffff")
            font_file = obj.get("font", "NotoSansBengali-Regular.ttf")
            stroke_width = max(0, int(obj.get("strokeWidth", 0)))
            stroke_color = obj.get("strokeColor", "#000000")
            shadow = obj.get("shadow", False)
            shadow_blur = max(1, int(obj.get("shadowBlur", 8)))
            shadow_color = obj.get("shadowColor", "#000000")
            shadow_x = int(obj.get("shadowX", 4))
            shadow_y = int(obj.get("shadowY", 4))
            opacity = max(0.0, min(1.0, float(obj.get("opacity", 1.0))))
            rotation = float(obj.get("rotation", 0))
            glow = obj.get("glow", False)
            outline_only = obj.get("outlineOnly", False)
            neon = obj.get("neon", False)
            double_stroke = obj.get("doubleStroke", False)
            gradient = obj.get("gradient", False)
            gradient_color2 = obj.get("gradientColor2", "#ff6600")

            font_path = os.path.join(FONT_DIR, font_file)
            if not os.path.exists(font_path):
                available = [f for f in os.listdir(FONT_DIR) if f.endswith(".ttf")]
                font_path = os.path.join(FONT_DIR, available[0]) if available else None

            try:
                font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            alpha = int(opacity * 255)
            tc = hex_to_rgba(color, alpha)
            sc = hex_to_rgba(stroke_color, alpha)
            shc = hex_to_rgba(shadow_color, 160)

            txt_layer = Image.new("RGBA", composite.size, (0,0,0,0))

            # Shadow
            if shadow:
                sl = Image.new("RGBA", composite.size, (0,0,0,0))
                sd = ImageDraw.Draw(sl)
                for i in range(3):
                    sd.text((x+shadow_x+i, y+shadow_y+i), text, font=font, fill=shc)
                sl = sl.filter(ImageFilter.GaussianBlur(shadow_blur))
                txt_layer = Image.alpha_composite(txt_layer, sl)

            # Neon
            if neon:
                for br in [12, 8, 4, 2]:
                    gl = Image.new("RGBA", composite.size, (0,0,0,0))
                    gd = ImageDraw.Draw(gl)
                    gd.text((x, y), text, font=font, fill=tc)
                    gl = gl.filter(ImageFilter.GaussianBlur(br))
                    txt_layer = Image.alpha_composite(txt_layer, gl)

            # Soft glow
            elif glow:
                gl = Image.new("RGBA", composite.size, (0,0,0,0))
                gd = ImageDraw.Draw(gl)
                gd.text((x, y), text, font=font, fill=tc)
                gl = gl.filter(ImageFilter.GaussianBlur(7))
                txt_layer = Image.alpha_composite(txt_layer, gl)

            draw = ImageDraw.Draw(txt_layer)

            # Double stroke
            if double_stroke and stroke_width > 0:
                outer = hex_to_rgba("#ffffff", alpha)
                draw.text((x, y), text, font=font, fill=(0,0,0,0),
                         stroke_width=stroke_width+5, stroke_fill=outer)
                draw.text((x, y), text, font=font, fill=(0,0,0,0),
                         stroke_width=stroke_width+2, stroke_fill=sc)

            # Gradient text (approximate with colored fill)
            if gradient:
                gc2 = hex_to_rgba(gradient_color2, alpha)
                blend = tuple(int((tc[i]+gc2[i])//2) for i in range(4))
                tc_use = blend
            else:
                tc_use = tc

            if outline_only:
                draw.text((x, y), text, font=font, fill=(0,0,0,0),
                         stroke_width=max(stroke_width, 3), stroke_fill=tc_use)
            else:
                if stroke_width > 0:
                    draw.text((x, y), text, font=font, fill=tc_use,
                             stroke_width=stroke_width, stroke_fill=sc)
                else:
                    draw.text((x, y), text, font=font, fill=tc_use)

            if rotation != 0:
                try:
                    bbox = font.getbbox(text)
                    cx = x + (bbox[2]-bbox[0])//2
                    cy = y + (bbox[3]-bbox[1])//2
                    txt_layer = txt_layer.rotate(-rotation, expand=False, center=(cx, cy))
                except:
                    txt_layer = txt_layer.rotate(-rotation, expand=False)

            composite = Image.alpha_composite(composite, txt_layer)

        output = io.BytesIO()
        composite.convert("RGB").save(output, format="PNG", quality=95)
        output.seek(0)
        img_b64 = base64.b64encode(output.read()).decode()
        return jsonify({"image": f"data:image/png;base64,{img_b64}"})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/download", methods=["POST"])
def download_image():
    try:
        data = request.json
        image_data = data.get("image")
        img_bytes = base64.b64decode(image_data.split(",")[1])
        return send_file(
            io.BytesIO(img_bytes),
            mimetype="image/png",
            as_attachment=True,
            download_name="bangla_typography.png"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
