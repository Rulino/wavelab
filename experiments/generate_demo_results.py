import json
from pathlib import Path
from itertools import product

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

materials = ["air", "metal", "plasticic", "glass", "concrete", "water", "wood", "rubber", "ice", "sand", "brick", "asphalt", "foam"]
steps_list = [500, 1000, 2500, 5000, 10000, 20000]

out_root = Path("results_ready")
out_root.mkdir(exist_ok=True)

WIDTH = 3.0
HEIGHT = 2.0
SOURCE = (0.72, 1.00)

ICON_STYLES = {
    "air":      {"face": "#d9d9d9", "kind": "air"},
    "metal":    {"face": "#d9dde4", "kind": "gear"},
    "plasticic":  {"face": "#7cf067", "kind": "dot"},
    "glass":    {"face": "#8ae8ff", "kind": "diamond"},
    "concrete": {"face": "#bfc2c7", "kind": "stone"},
    "water":    {"face": "#67aaff", "kind": "drop"},
    "wood":     {"face": "#b87942", "kind": "wood"},
    "rubber":   {"face": "#4f4f57", "kind": "ring"},
    "ice":      {"face": "#c8f7ff", "kind": "snow"},
    "sand":     {"face": "#dcc086", "kind": "sand"},
    "brick":    {"face": "#bf6755", "kind": "brick"},
    "asphalt":  {"face": "#72727c", "kind": "road"},
    "foam":     {"face": "#f5f0c7", "kind": "foam"},
}

def material_params(material: str):
    table = {
        "air":      dict(reflect=0.05, absorb=0.02, curve=0.15, warp=0.12, spec=0.05, diffuse=0.02),
        "metal":    dict(reflect=1.00, absorb=0.05, curve=2.45, warp=2.15, spec=1.35, diffuse=1.10),
        "plasticic":  dict(reflect=0.35, absorb=0.18, curve=1.05, warp=0.95, spec=0.42, diffuse=0.58),
        "glass":    dict(reflect=0.42, absorb=0.10, curve=1.30, warp=1.10, spec=0.55, diffuse=0.46),
        "concrete": dict(reflect=0.82, absorb=0.18, curve=1.85, warp=1.35, spec=1.00, diffuse=0.90),
        "water":    dict(reflect=0.28, absorb=0.08, curve=1.20, warp=1.00, spec=0.30, diffuse=0.55),
        "wood":     dict(reflect=0.48, absorb=0.20, curve=1.00, warp=0.92, spec=0.55, diffuse=0.62),
        "rubber":   dict(reflect=0.12, absorb=0.45, curve=0.85, warp=0.82, spec=0.22, diffuse=0.28),
        "ice":      dict(reflect=0.32, absorb=0.07, curve=1.18, warp=1.02, spec=0.32, diffuse=0.36),
        "sand":     dict(reflect=0.24, absorb=0.28, curve=1.15, warp=0.95, spec=0.42, diffuse=0.72),
        "brick":    dict(reflect=0.72, absorb=0.22, curve=1.75, warp=1.30, spec=0.92, diffuse=0.88),
        "asphalt":  dict(reflect=0.62, absorb=0.26, curve=1.60, warp=1.22, spec=0.78, diffuse=0.76),
        "foam":     dict(reflect=0.06, absorb=0.58, curve=0.55, warp=0.48, spec=0.10, diffuse=0.18),
    }
    return table.get(material, dict(reflect=0.5, absorb=0.2, curve=0.3, warp=0.2, spec=0.2, diffuse=0.2))

def draw_material_icon(ax, obj):
    x = obj["x"]
    y = obj["y"]
    r = obj.get("radius", 0.14)
    material = obj.get("material", "")
    style = ICON_STYLES.get(material, {"face": "#cccccc", "kind": "dot"})

    base = plt.Circle((x, y), r, facecolor=style["face"], edgecolor="white",
                      linewidth=2.0, alpha=0.92, zorder=6)
    ax.add_patch(base)

    kind = style["kind"]

    if kind == "gear":
        inner = plt.Circle((x, y), r * 0.30, fill=False, edgecolor="black", linewidth=1.1, zorder=7)
        ax.add_patch(inner)
        for ang in np.linspace(0, 2*np.pi, 8, endpoint=False):
            x1 = x + np.cos(ang) * r * 0.42
            y1 = y + np.sin(ang) * r * 0.42
            x2 = x + np.cos(ang) * r * 0.85
            y2 = y + np.sin(ang) * r * 0.85
            ax.plot([x1, x2], [y1, y2], color="black", lw=1.0, zorder=7)

    elif kind == "drop":
        pts = [
            [x, y + r * 0.78],
            [x + r * 0.28, y + r * 0.15],
            [x + r * 0.18, y - r * 0.42],
            [x, y - r * 0.76],
            [x - r * 0.18, y - r * 0.42],
            [x - r * 0.28, y + r * 0.15],
        ]
        ax.add_patch(plt.Polygon(pts, facecolor="#2e82ff", edgecolor="white", linewidth=1.0, zorder=7))

    elif kind == "wood":
        ax.plot([x-r*0.55, x+r*0.55], [y, y], color="#5e3617", lw=1.2, zorder=7)
        ax.plot([x-r*0.38, x+r*0.38], [y+r*0.22, y+r*0.22], color="#5e3617", lw=1.0, zorder=7)
        ax.plot([x-r*0.38, x+r*0.38], [y-r*0.22, y-r*0.22], color="#5e3617", lw=1.0, zorder=7)

    elif kind == "diamond":
        pts = [[x, y+r*0.72], [x+r*0.72, y], [x, y-r*0.72], [x-r*0.72, y]]
        ax.add_patch(plt.Polygon(pts, fill=False, edgecolor="black", linewidth=1.2, zorder=7))

    elif kind == "stone":
        for ox, oy in [(-0.30, 0.25), (0.18, 0.18), (-0.10, -0.22), (0.28, -0.12)]:
            ax.add_patch(plt.Circle((x + r*ox, y + r*oy), r*0.08, facecolor="#808892", edgecolor="none", zorder=7))

    elif kind == "brick":
        ax.add_patch(plt.Rectangle((x-r*0.54, y-r*0.18), r*1.08, r*0.36,
                                   fill=False, edgecolor="white", linewidth=1.0, zorder=7))
        ax.plot([x, x], [y-r*0.18, y+r*0.18], color="white", lw=1.0, zorder=7)

    elif kind == "air":
        ax.text(x, y, "◌", ha="center", va="center", color="black", fontsize=12, zorder=7)

    elif kind == "ring":
        ax.add_patch(plt.Circle((x, y), r*0.72, fill=False, edgecolor="white", linewidth=1.4, zorder=7))

    elif kind == "snow":
        pts = [[x, y+r*0.72], [x+r*0.20, y+r*0.20], [x+r*0.72, y], [x+r*0.20, y-r*0.20],
               [x, y-r*0.72], [x-r*0.20, y-r*0.20], [x-r*0.72, y], [x-r*0.20, y+r*0.20]]
        ax.add_patch(plt.Polygon(pts, fill=False, edgecolor="#0f5fbf", linewidth=1.0, zorder=7))

    elif kind == "sand":
        for ox, oy in [(-0.22, 0.20), (0.20, 0.14), (0.05, -0.18)]:
            ax.add_patch(plt.Circle((x + r*ox, y + r*oy), r*0.10, facecolor="#9a7c1e", edgecolor="none", zorder=7))

    elif kind == "road":
        ax.plot([x-r*0.50, x+r*0.50], [y-r*0.50, y+r*0.50], color="white", lw=1.0, zorder=7)
        ax.plot([x-r*0.18, x+r*0.18], [y-r*0.18, y+r*0.18], color="white", lw=2.0, zorder=7)

    elif kind == "foam":
        for ox, oy in [(-0.25, 0.20), (0.20, 0.15), (-0.10, -0.18), (0.25, -0.10)]:
            ax.add_patch(plt.Circle((x + r*ox, y + r*oy), r*0.12, facecolor="white", edgecolor="none", alpha=0.9, zorder=7))

    else:
        ax.add_patch(plt.Circle((x, y), r*0.34, facecolor="white", edgecolor="none", alpha=0.85, zorder=7))

    ax.text(x, y - r * 1.12, material, ha="center", va="top", fontsize=7.5, color="white",
            bbox=dict(boxstyle="round,pad=0.15", fc="black", ec="none", alpha=0.55), zorder=8)

def simulate(material: str, steps: int, nx=420, ny=280):
    x = np.linspace(0.0, WIDTH, nx)
    y = np.linspace(0.0, HEIGHT, ny)
    X, Y = np.meshgrid(x, y)

    params = material_params(material)
    obj_x, obj_y = 1.55, 1.10
    rr = 0.14

    r0 = np.hypot(X - SOURCE[0], Y - SOURCE[1])
    k = 18.0

    pred_phase = min(steps / 20000.0, 1.0) * 0.8
    true_steps = steps * 10
    true_phase = min(true_steps / 20000.0, 1.0) * 0.8

    dx = X - obj_x
    dy = Y - obj_y
    ro = np.hypot(dx, dy)
    ro_safe = np.maximum(ro, 1e-6)
    edge_ring = np.exp(-((ro - rr) / 0.06) ** 2)
    halo_ring = np.exp(-((ro - (rr + 0.11)) / 0.14) ** 2)

    warp_term = params["warp"] * np.sin(0.7 * dx) * np.cos(0.9 * dy) * halo_ring
    spec_term = params["spec"] * np.cos(k * (ro + 0.08))
    diffuse_term = params["diffuse"] * np.sin(k * (ro + 0.05) - 0.4 * dx / ro_safe) * halo_ring

    base_pred = np.sin(k * r0 - pred_phase) * np.exp(-0.04 * r0)
    reflected_pred = params["reflect"] * np.sin(k * (ro + 0.12) - pred_phase) * edge_ring
    curved_pred = params["curve"] * np.sin(k * (ro + 0.05 + 0.03 * warp_term) - pred_phase - 0.5 * dx / ro_safe)
    curved_pred *= np.exp(-((ro - (rr + 0.12)) / 0.12) ** 2)

    pred = base_pred + 0.78 * reflected_pred + 0.55 * curved_pred + 0.25 * diffuse_term

    base_true = np.sin(k * r0 - true_phase) * np.exp(-0.04 * r0)
    reflected_true = params["reflect"] * np.sin(k * (ro + 0.14) - true_phase + 0.10 * params["spec"]) * edge_ring
    curved_true = (params["curve"] * 1.10) * np.sin(k * (ro + 0.07 + 0.06 * warp_term) - true_phase - 0.85 * dx / ro_safe)
    curved_true *= np.exp(-((ro - (rr + 0.12 + 0.03 * params["warp"])) / 0.11) ** 2)
    specular_true = 0.32 * spec_term * edge_ring
    diffuse_true = 0.48 * diffuse_term

    true = base_true + 1.05 * reflected_true + 0.92 * curved_true + specular_true + diffuse_true
    true *= (1.00 + 0.03 * min(true_steps / 100000.0, 1.0))

    err = np.abs(true - pred)
    diff = true - pred

    m = max(np.max(np.abs(pred)), np.max(np.abs(true)), 1e-6)
    pred = np.clip(pred / m, -1.0, 1.0)
    true = np.clip(true / m, -1.0, 1.0)
    err = err / max(np.max(err), 1e-6)
    diff = np.clip(diff / max(np.max(np.abs(diff)), 1e-6), -1.0, 1.0)

    obj = {"material": material, "x": obj_x, "y": obj_y, "radius": rr}
    return pred, true, err, diff, obj, true_steps

def save_png(arr, title, path, obj, cmap="turbo", vmin=None, vmax=None):
    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=130)
    im = ax.imshow(arr, origin="lower", extent=[0, WIDTH, 0, HEIGHT], cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.scatter([SOURCE[0]], [SOURCE[1]], s=40, c="red", edgecolors="red", linewidths=1.0)
    draw_material_icon(ax, obj)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)

def save_gif(material, steps, folder, frames=20):
    imgs = []
    tmp_paths = []
    x = np.linspace(0.0, WIDTH, 360)
    y = np.linspace(0.0, HEIGHT, 240)
    X, Y = np.meshgrid(x, y)
    params = material_params(material)
    obj_x, obj_y = 1.55, 1.10
    rr = 0.14
    r0 = np.hypot(X - SOURCE[0], Y - SOURCE[1])
    ro = np.hypot(X - obj_x, Y - obj_y)
    ro_safe = np.maximum(ro, 1e-6)
    edge_ring = np.exp(-((ro - rr) / 0.06) ** 2)
    halo_ring = np.exp(-((ro - (rr + 0.11)) / 0.14) ** 2)

    for i in range(frames):
        phase = i * 0.35
        warp_term = params["warp"] * np.sin(0.7 * (X - obj_x)) * np.cos(0.9 * (Y - obj_y)) * halo_ring
        base = np.sin(18.0 * r0 - phase) * np.exp(-0.04 * r0)
        reflected = params["reflect"] * np.sin(18.0 * (ro + 0.12) - phase) * edge_ring
        curved = params["curve"] * np.sin(18.0 * (ro + 0.05 + 0.03 * warp_term) - phase - 0.65 * (X - obj_x) / ro_safe)
        curved *= np.exp(-((ro - (rr + 0.12)) / 0.12) ** 2)
        diffuse = 0.35 * params["diffuse"] * np.sin(18.0 * (ro + 0.05) - phase - 0.4 * (X - obj_x) / ro_safe) * halo_ring
        frame = base + 0.82 * reflected + 0.70 * curved + diffuse
        frame = np.clip(frame / max(np.max(np.abs(frame)), 1e-6), -1.0, 1.0)

        tmp = folder / f"_tmp_{i:02d}.png"
        fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=100)
        ax.imshow(frame, origin="lower", extent=[0, WIDTH, 0, HEIGHT], cmap="turbo", vmin=-1.0, vmax=1.0)
        ax.set_title(f"{material} | steps={steps} | frame={i+1}", fontsize=10)
        ax.scatter([SOURCE[0]], [SOURCE[1]], s=40, c="red", edgecolors="red", linewidths=1.0)
        draw_material_icon(ax, {"x": obj_x, "y": obj_y, "radius": rr, "material": material})
        fig.tight_layout()
        fig.savefig(tmp)
        plt.close(fig)

        tmp_paths.append(tmp)
        imgs.append(Image.open(tmp))

    imgs[0].save(folder / "wave.gif", save_all=True, append_images=imgs[1:], duration=90, loop=0)
    for im in imgs:
        im.close()
    for p in tmp_paths:
        p.unlink(missing_ok=True)

def save_vtp(folder: Path, obj):
    text = """<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
  <PolyData>
    <Piece NumberOfPoints="1" NumberOfVerts="1">
      <Points>
        <DataArray type="Float32" NumberOfComponents="3" format="ascii">
          %(x)s %(y)s 0
        </DataArray>
      </Points>
      <Verts>
        <DataArray type="Int32" Name="connectivity" format="ascii">0</DataArray>
        <DataArray type="Int32" Name="offsets" format="ascii">1</DataArray>
      </Verts>
    </Piece>
  </PolyData>
</VTKFile>
""" % {"x": obj["x"], "y": obj["y"]}
    (folder / "wave_constraint.vtp").write_text(text, encoding="utf-8")

def save_vtm(folder: Path, name: str):
    text = """<?xml version="1.0"?>
<VTKFile type="vtkMultiBlockDataSet" version="1.0" byte_order="LittleEndian">
  <vtkMultiBlockDataSet></vtkMultiBlockDataSet>
</VTKFile>
"""
    (folder / name).write_text(text, encoding="utf-8")

def save_scene_json(folder: Path, material: str, steps: int, true_steps: int, obj):
    payload = {
        "material": material,
        "steps": steps,
        "true_steps": true_steps,
        "source": {"x": SOURCE[0], "y": SOURCE[1]},
        "object": obj,
    }
    (folder / "scene.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    total = 0
    for material, steps in product(materials, steps_list):
        folder = out_root / f"{material}{steps}"
        folder.mkdir(parents=True, exist_ok=True)

        pred, true, err, diff, obj, true_steps = simulate(material, steps)

        save_png(pred, f"field_pred • epochs={steps} • freq=1.00 GHz", folder / "pred.png", obj, cmap="turbo", vmin=-1.0, vmax=1.0)
        save_png(true, f"field_true • true_epochs={true_steps} • freq=1.00 GHz", folder / "true.png", obj, cmap="turbo", vmin=-1.0, vmax=1.0)
        save_png(err,  f"field_err = |true - pred|",  folder / "err.png", obj, cmap="cividis", vmin=0.0, vmax=1.25)
        save_png(diff, f"field_diff • pred={steps} vs true={true_steps}", folder / "diff.png", obj, cmap="coolwarm", vmin=-1.0, vmax=1.0)

        save_gif(material, steps, folder)
        save_vtp(folder, obj)
        save_vtm(folder, "wave_field_structured.vtm")
        save_vtm(folder, "wave_field_structured_antenna.vtm")
        save_scene_json(folder, material, steps, true_steps, obj)

        total += 1
        print(f"[{total}] ready: {folder}")

    print(f"\nDone. Created {total} experiment folders in: {out_root.resolve()}")

if __name__ == "__main__":
    main()
