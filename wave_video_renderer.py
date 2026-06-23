import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    import yaml
except Exception as e:
    raise SystemExit("Install PyYAML: pip install pyyaml") from e


DEFAULT_MATERIALS = {
    "air":      {"absorption": 0.025, "R": 0.00, "T": 1.00, "scatter": 0.00, "color": "#94a3b8"},
    "concrete": {"absorption": 0.45, "R": 0.55, "T": 0.42, "scatter": 0.45, "color": "#d1d5db"},
    "metal":    {"absorption": 0.20, "R": 0.95, "T": 0.08, "scatter": 0.75, "color": "#fbbf24"},
    "glass":    {"absorption": 0.10, "R": 0.25, "T": 0.78, "scatter": 0.20, "color": "#38bdf8"},
    "plastic":  {"absorption": 0.18, "R": 0.18, "T": 0.86, "scatter": 0.18, "color": "#60a5fa"},
    "water":    {"absorption": 0.16, "R": 0.20, "T": 0.82, "scatter": 0.28, "color": "#3b82f6"},
}

MATERIAL_LABEL_COLORS = {
    "concrete": "#d1d5db",
    "metal": "#fbbf24",
    "glass": "#38bdf8",
    "plastic": "#60a5fa",
    "water": "#3b82f6",
    "air": "#94a3b8",
}

def load_scene(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("materials", {})
    for k, v in DEFAULT_MATERIALS.items():
        data["materials"].setdefault(k, v)
        for pk, pv in v.items():
            data["materials"][k].setdefault(pk, pv)
    return data

def hex_to_rgb(h):
    h = str(h).strip().lstrip("#")
    if len(h) != 6:
        return (180, 180, 180)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def world_to_px(x, y, W, H, world):
    xmin, xmax = world["xmin"], world["xmax"]
    ymin, ymax = world["ymin"], world["ymax"]
    px = int((x - xmin) / (xmax - xmin) * W)
    py = int((ymax - y) / (ymax - ymin) * H)
    return px, py

def length_to_px(v, W, H, world):
    sx = W / (world["xmax"] - world["xmin"])
    sy = H / (world["ymax"] - world["ymin"])
    return int(v * (sx + sy) * 0.5)

def rotate_points(points, angle_deg, center):
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    cx, cy = center
    out = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return out

def shape_mask(X, Y, obj):
    x, y = float(obj.get("x", 0)), float(obj.get("y", 0))
    shape = str(obj.get("shape", "circle")).lower()
    angle = math.radians(float(obj.get("angle", 0.0)))
    ca, sa = math.cos(angle), math.sin(angle)
    dx, dy = X - x, Y - y
    lx = dx * ca + dy * sa
    ly = -dx * sa + dy * ca

    if shape == "circle":
        r = float(obj.get("r", obj.get("radius", 0.1)))
        return (lx * lx + ly * ly) <= r * r

    if shape in ("rectangle", "square"):
        w = float(obj.get("width", 0.2))
        h = float(obj.get("height", w if shape == "square" else 0.16))
        return (np.abs(lx) <= w / 2) & (np.abs(ly) <= h / 2)

    if shape == "triangle":
        w = float(obj.get("width", 0.22))
        h = float(obj.get("height", 0.20))
        # upright isosceles triangle, barycentric sign test
        x1, y1 = 0.0, h / 2
        x2, y2 = -w / 2, -h / 2
        x3, y3 = w / 2, -h / 2
        e1 = (lx - x1) * (y2 - y1) - (ly - y1) * (x2 - x1)
        e2 = (lx - x2) * (y3 - y2) - (ly - y2) * (x3 - x2)
        e3 = (lx - x3) * (y1 - y3) - (ly - y3) * (x1 - x3)
        return ((e1 >= 0) & (e2 >= 0) & (e3 >= 0)) | ((e1 <= 0) & (e2 <= 0) & (e3 <= 0))

    r = float(obj.get("r", 0.1))
    return (lx * lx + ly * ly) <= r * r

def draw_shape(draw, obj, W, H, world, idx, materials):
    mat = str(obj.get("material", "air")).lower()
    col = hex_to_rgb(materials.get(mat, {}).get("color", MATERIAL_LABEL_COLORS.get(mat, "#d1d5db")))
    x, y = float(obj.get("x", 0)), float(obj.get("y", 0))
    px, py = world_to_px(x, y, W, H, world)
    shape = str(obj.get("shape", "circle")).lower()

    outline = (255, 255, 255, 255)
    shadow = (20, 30, 45, 160)

    if shape == "circle":
        r = length_to_px(float(obj.get("r", obj.get("radius", 0.1))), W, H, world)
        bbox = [px - r, py - r, px + r, py + r]
        draw.ellipse([bbox[0]+5, bbox[1]+5, bbox[2]+5, bbox[3]+5], fill=shadow)
        draw.ellipse(bbox, fill=col + (225,), outline=outline, width=3)
    elif shape in ("rectangle", "square"):
        ww = length_to_px(float(obj.get("width", 0.2)), W, H, world)
        hh = length_to_px(float(obj.get("height", ww if shape == "square" else 0.16)), W, H, world)
        pts = [(px - ww/2, py - hh/2), (px + ww/2, py - hh/2), (px + ww/2, py + hh/2), (px - ww/2, py + hh/2)]
        pts = rotate_points(pts, float(obj.get("angle", 0)), (px, py))
        draw.polygon([(a+5,b+5) for a,b in pts], fill=shadow)
        draw.polygon(pts, fill=col + (230,), outline=outline)
        draw.line(pts + [pts[0]], fill=outline, width=3)
    elif shape == "triangle":
        ww = length_to_px(float(obj.get("width", 0.22)), W, H, world)
        hh = length_to_px(float(obj.get("height", 0.20)), W, H, world)
        pts = [(px, py - hh/2), (px - ww/2, py + hh/2), (px + ww/2, py + hh/2)]
        pts = rotate_points(pts, float(obj.get("angle", 0)), (px, py))
        draw.polygon([(a+5,b+5) for a,b in pts], fill=shadow)
        draw.polygon(pts, fill=col + (225,), outline=outline)
        draw.line(pts + [pts[0]], fill=outline, width=3)

    # number bubble
    rr = 14
    bx, by = px + 20, py - 20
    draw.ellipse([bx-rr, by-rr, bx+rr, by+rr], fill=(55, 65, 81, 230), outline=(255,255,255,255), width=2)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    draw.text((bx, by), str(idx), anchor="mm", fill=(255,255,255,255), font=font)

def colormap_turbo_like(v):
    # v in [0, 1], handcrafted scientific teal/blue/yellow-green palette
    stops = np.array([
        [30, 30, 115],
        [28, 90, 160],
        [20, 155, 145],
        [38, 190, 105],
        [175, 225, 55],
        [255, 225, 85],
    ], dtype=np.float32)
    x = np.clip(v, 0, 1) * (len(stops) - 1)
    i = np.floor(x).astype(np.int32)
    j = np.clip(i + 1, 0, len(stops) - 1)
    t = (x - i)[..., None]
    rgb = stops[i] * (1 - t) + stops[j] * t
    return rgb.astype(np.uint8)

def compute_field(X, Y, data, t, frame_index):
    scene = data["scene"]
    src = scene["source"]
    objs = scene.get("objects", [])
    mats = data["materials"]

    x0, y0 = float(src.get("x0", 0.7)), float(src.get("y0", 1.0))
    A = float(src.get("amplitude", 1.0))

    dx = X - x0
    dy = Y - y0
    r = np.sqrt(dx * dx + dy * dy) + 1e-6

    # main wave
    k = 72.0
    omega = 9.5
    field = A * np.sin(k * r - omega * t) * np.exp(-0.33 * r) / np.sqrt(0.25 + r)

    # object effects: shadow, reflection, diffraction
    shadow = np.ones_like(field)
    for obj in objs:
        ox, oy = float(obj.get("x", 0)), float(obj.get("y", 0))
        mat = str(obj.get("material", "air")).lower()
        prop = mats.get(mat, {})
        R = float(prop.get("R", 0.2))
        T = float(prop.get("T", 0.8))
        absorption = float(prop.get("absorption", 0.2))
        scatter = float(prop.get("scatter", 0.2))

        odx = X - ox
        ody = Y - oy
        ro = np.sqrt(odx * odx + ody * ody) + 1e-6
        rso = math.sqrt((ox - x0)**2 + (oy - y0)**2) + 1e-6

        # reflected / secondary waves. The reflection is weighted by the actual object
        # shape mask, so square/rectangle/triangle objects leave a geometry-aware imprint
        # instead of looking like a purely circular point reflection.
        mask = shape_mask(X, Y, obj).astype(np.float32)
        shape_imprint = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=9))
        shape_imprint = np.asarray(shape_imprint, dtype=np.float32) / 255.0
        phase = k * (rso + ro) - omega * t + R * 2.3
        reflected = R * (0.28 + 0.30 * shape_imprint) * np.sin(phase) * np.exp(-0.62 * ro) / np.sqrt(0.30 + ro)
        field += reflected

        # diffraction halo around object
        halo = np.exp(-(ro / (0.14 + scatter * 0.18)) ** 2)
        field += scatter * 0.35 * halo * np.sin(k * ro - omega * t + frame_index * 0.035)

        # directional shadow behind object
        vx, vy = ox - x0, oy - y0
        vl = math.sqrt(vx*vx + vy*vy) + 1e-6
        vx, vy = vx / vl, vy / vl
        px = X - ox
        py = Y - oy
        along = px * vx + py * vy
        perp = np.abs(px * (-vy) + py * vx)
        cone_width = 0.055 + 0.26 * np.maximum(along, 0)
        cone = (along > 0) * np.exp(-(perp / (cone_width + 1e-6)) ** 2) * np.exp(-0.35 * along)
        shadow *= 1.0 - cone * min(0.72, absorption * 0.42 + (1.0 - T) * 0.55)

        # inside object attenuation using the actual geometry and real scene scale.
        mask = shape_mask(X, Y, obj)
        shadow[mask] *= max(0.18, T * 0.72)

    field *= shadow

    # fine high-frequency interference
    field += 0.075 * np.sin(108.0 * X + 38.0 * Y - 1.35 * omega * t)
    return field

SHAPE_NAMES_SK = {
    "circle": "kruh",
    "square": "štvorec",
    "rectangle": "obdĺžnik",
    "triangle": "trojuholník",
}

MATERIAL_NAMES_SK = {
    "air": "vzduch",
    "glass": "sklo",
    "concrete": "betón",
    "metal": "kov",
    "plastic": "plast",
    "water": "voda",
    "foam": "pena",
    "rubber": "guma",
    "wood": "drevo",
    "sand": "piesok",
    "brick": "tehla",
    "asphalt": "asfalt",
}

def draw_material_side_panel(draw, panel_box, objects, materials, font_title, font_med, font_small):
    """Draw separate material/physics panel outside the wave field."""
    x0, y0, x1, y1 = panel_box
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=16,
        fill=(8, 18, 32, 235),
        outline=(220, 230, 240, 210),
        width=2,
    )

    title_y = y0 + 36
    draw.text(
        ((x0 + x1) // 2, title_y),
        "Materiály a fyzikálne parametre",
        anchor="mm",
        fill=(255, 255, 255, 255),
        font=font_title,
    )

    row_y = y0 + 82
    row_h = 42
    for i, obj in enumerate(objects[:8], start=1):
        mat_raw = str(obj.get("material", "air")).lower()
        shape_raw = str(obj.get("shape", "circle")).lower()
        mat = MATERIAL_NAMES_SK.get(mat_raw, mat_raw)
        shape = SHAPE_NAMES_SK.get(shape_raw, shape_raw)
        props = materials.get(mat_raw, {}) if isinstance(materials, dict) else {}
        color = hex_to_rgb(props.get("color", MATERIAL_LABEL_COLORS.get(mat_raw, "#d1d5db")))

        if shape_raw == "circle":
            size_txt = f"r={float(obj.get('r', obj.get('radius', 0.0))):.2f}"
        else:
            size_txt = f"{float(obj.get('width', 0.0)):.2f}×{float(obj.get('height', 0.0)):.2f}"

        R = float(props.get("R", props.get("reflection", 0.0)))
        T = float(props.get("T", props.get("transmission", 1.0)))
        absorption = float(props.get("absorption", 0.0))
        scatter = float(props.get("scatter", 0.0))

        yy = row_y + (i - 1) * row_h
        draw.rounded_rectangle(
            [x0 + 28, yy - 12, x0 + 50, yy + 10],
            radius=4,
            fill=color + (240,),
            outline=(255, 255, 255, 230),
            width=1,
        )
        line = f"{i}. {mat} · {shape} · {size_txt} · R={R:.2f} T={T:.2f} α={absorption:.2f} S={scatter:.2f}"
        draw.text((x0 + 64, yy), line, anchor="lm", fill=(245, 248, 252, 255), font=font_small)

    sep_y = row_y + min(len(objects), 8) * row_h + 8
    draw.line([x0 + 28, sep_y, x1 - 28, sep_y], fill=(230, 230, 230, 140), width=1)

    desc_y = sep_y + 36
    info_lines = [
        ("R", "odrazivosť (reflection)"),
        ("T", "priepustnosť (transmission)"),
        ("α", "absorpcia (útlm v materiáli)"),
        ("S", "rozptyl (scattering)"),
    ]
    for j, (sym, meaning) in enumerate(info_lines):
        yy = desc_y + j * 34
        draw.text((x0 + 28, yy), sym, anchor="lm", fill=(255, 255, 255, 255), font=font_med)
        draw.text((x0 + 58, yy), f"– {meaning}", anchor="lm", fill=(235, 240, 245, 255), font=font_small)

    bar_box_y = desc_y + 4 * 34 + 36
    draw.rounded_rectangle(
        [x0 + 28, bar_box_y, x1 - 28, y1 - 26],
        radius=8,
        fill=(5, 15, 28, 120),
        outline=(230, 230, 230, 110),
        width=1,
    )
    draw.text(
        ((x0 + x1) // 2, bar_box_y + 32),
        "Intenzita vlnenia (normalizovaná)",
        anchor="mm",
        fill=(255, 255, 255, 255),
        font=font_med,
    )
    gx0, gy0 = x0 + 52, bar_box_y + 62
    gx1, gy1 = x1 - 52, gy0 + 22
    grad_w = max(1, gx1 - gx0)
    grad = np.linspace(0, 1, grad_w, dtype=np.float32)[None, :]
    grad_rgb = colormap_turbo_like(np.repeat(grad, gy1 - gy0, axis=0))
    grad_img = Image.fromarray(grad_rgb, "RGB")
    return grad_img, (gx0, gy0, gx1, gy1), (x0 + 52, gy1 + 20), (x1 - 52, gy1 + 20)


def render_frame(data, out_png, W=1280, H=760, frame_index=0, frames=96, overlay=True):
    scene = data["scene"]
    world = scene.get("world", {"xmin": 0, "xmax": 3, "ymin": 0, "ymax": 2})

    # When overlay=True, the video is split into two separate zones:
    # left = wave field, right = material/physics information panel.
    final_W, final_H = int(W), int(H)
    panel_w = 470 if overlay else 0
    gap = 24 if overlay else 0
    margin = 18 if overlay else 0
    sim_W = final_W - panel_w - gap - margin * 2 if overlay else final_W
    sim_W = max(520, sim_W)
    sim_H = final_H - margin * 2 if overlay else final_H

    x = np.linspace(world["xmin"], world["xmax"], sim_W)
    y = np.linspace(world["ymax"], world["ymin"], sim_H)
    X, Y = np.meshgrid(x, y)

    t = 2.0 * math.pi * frame_index / frames
    field = compute_field(X, Y, data, t, frame_index)

    # normalize with contrast
    v = np.tanh(field * 1.25)
    v = (v + 1) / 2
    rgb = colormap_turbo_like(v)

    img = Image.fromarray(rgb, "RGB").convert("RGBA")

    # bloom/glow pass
    bright = np.clip((v - 0.55) / 0.45, 0, 1)
    glow_rgb = colormap_turbo_like(bright)
    glow = Image.fromarray(glow_rgb, "RGB").filter(ImageFilter.GaussianBlur(radius=7)).convert("RGBA")
    img = Image.blend(img, glow, 0.28)

    # subtle dark vignette
    yy, xx = np.mgrid[0:sim_H, 0:sim_W]
    cx, cy = sim_W / 2, sim_H / 2
    d = np.sqrt(((xx - cx) / sim_W) ** 2 + ((yy - cy) / sim_H) ** 2)
    vig = np.clip(1.10 - d * 1.25, 0.72, 1.0)
    arr = np.asarray(img).astype(np.float32)
    arr[..., :3] *= vig[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    if overlay:
        # Draw only source and objects on top of the wave field.
        wave_overlay = Image.new("RGBA", (sim_W, sim_H), (0, 0, 0, 0))
        draw_wave = ImageDraw.Draw(wave_overlay)
        try:
            font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
            font_med = ImageFont.truetype("DejaVuSans-Bold.ttf", 21)
            font_small = ImageFont.truetype("DejaVuSans.ttf", 17)
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        except Exception:
            font_big = font_med = font_small = font_title = ImageFont.load_default()

        src = scene["source"]
        sx, sy = world_to_px(float(src["x0"]), float(src["y0"]), sim_W, sim_H, world)
        draw_wave.ellipse([sx-10, sy-10, sx+10, sy+10], fill=(244,63,94,255), outline=(255,255,255,255), width=3)
        draw_wave.text((sx+18, sy), "SRC", anchor="lm", fill=(255,255,255,255), font=font_big)

        for i, obj in enumerate(scene.get("objects", []), start=1):
            draw_shape(draw_wave, obj, sim_W, sim_H, world, i, data["materials"])

        img = Image.alpha_composite(img, wave_overlay)

        # Create one full frame: wave field on the left, panel outside the field on the right.
        final = Image.new("RGBA", (final_W, final_H), (3, 10, 20, 255))
        final_draw = ImageDraw.Draw(final, "RGBA")
        final_draw.rounded_rectangle(
            [margin, margin, margin + sim_W, margin + sim_H],
            radius=10,
            fill=(0, 0, 0, 0),
            outline=(230, 230, 230, 130),
            width=2,
        )
        final.paste(img, (margin, margin), img)

        panel_x0 = margin + sim_W + gap
        panel_y0 = margin
        panel_x1 = final_W - margin
        panel_y1 = final_H - margin
        result = draw_material_side_panel(
            final_draw,
            (panel_x0, panel_y0, panel_x1, panel_y1),
            scene.get("objects", []),
            data["materials"],
            font_title,
            font_med,
            font_small,
        )
        grad_img, grad_box, min_pos, max_pos = result
        final.paste(grad_img, grad_box[:2])
        final_draw.rectangle(grad_box, outline=(255, 255, 255, 220), width=1)
        final_draw.text(min_pos, "min", anchor="lm", fill=(235, 240, 245, 255), font=font_small)
        final_draw.text(max_pos, "max", anchor="rm", fill=(235, 240, 245, 255), font=font_small)
        img = final

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_png, quality=96)
    return out_png

def render_animation(scene_path, out_dir, frames=96, width=1280, height=760, fps=24):
    data = load_scene(scene_path)
    out_dir = Path(out_dir)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = []
    for i in range(frames):
        p = frames_dir / f"frame_{i:04d}.png"
        render_frame(data, p, W=width, H=height, frame_index=i, frames=frames, overlay=True)
        frame_paths.append(p)
        print(f"[render] {i+1}/{frames}: {p}", flush=True)

    imgs = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in frame_paths]
    gif_path = out_dir / "wave_animation.gif"
    imgs[0].save(gif_path, save_all=True, append_images=imgs[1:], duration=int(1000/fps), loop=0, optimize=False)
    print(f"[done] {gif_path}", flush=True)
    return gif_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="scene.yaml")
    ap.add_argument("--out", default="results_live")
    ap.add_argument("--frames", type=int, default=96)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=760)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--one-frame", action="store_true")
    args = ap.parse_args()

    if args.one_frame:
        data = load_scene(args.scene)
        render_frame(data, Path(args.out) / "frame0.png", W=args.width, H=args.height, frame_index=0, frames=args.frames, overlay=True)
    else:
        render_animation(args.scene, args.out, frames=args.frames, width=args.width, height=args.height, fps=args.fps)

if __name__ == "__main__":
    main()
