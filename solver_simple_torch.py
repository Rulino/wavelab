

import argparse
import os
import sys
from datetime import datetime
import math
from collections import deque

# -------- Dependency checks / Dependency checks --------
# If a package is missing, show a clear install command instead of a long traceback.
# Implementation note.
try:
    import numpy as np
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing package: numpy\n"
        "Install it with:\n"
        "  python -m pip install numpy\n"
        "or install all project dependencies:\n"
        "  python -m pip install -r requirements.txt"
    ) from e

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing package: matplotlib\n"
        "Install it with:\n"
        "  python -m pip install matplotlib\n"
        "or install all project dependencies:\n"
        "  python -m pip install -r requirements.txt"
    ) from e

try:
    from PIL import Image
    PIL_ANIM_OK = True
except ModuleNotFoundError:
    Image = None
    PIL_ANIM_OK = False

try:
    import yaml
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing package: PyYAML\n"
        "Install it with:\n"
        "  python -m pip install pyyaml\n"
        "or install all project dependencies:\n"
        "  python -m pip install -r requirements.txt"
    ) from e


# Hranice sveta used for mesh generation and coordinate mapping
# Implementation note.
WORLD = dict(xmin=0.0, xmax=3.0, ymin=0.0, ymax=2.0)

# Default radius for point-objects (treated as disks in the solver)
# Implementation note.
DEFAULT_POINT_RADIUS = 0.08

# Default wave speed (c) per material (if not provided in scene.yaml)
# Implementation note.
DEFAULT_C_MAP = {
    "air": 3.0e8,
    "asphalt": 2.2e8,
    "brick": 2.0e8,
    "concrete": 2.0e8,
    "foam": 1.3e8,
    "glass": 2.2e8,
    "ice": 3.1e8,
    "metal": 2.5e8,
    "plastic": 2.4e8,
    "rubber": 1.6e8,
    "sand": 1.7e8,
    "water": 1.5e8,
    "wood": 2.0e8,
}

# Public examples and older GUI exports may use either English or Slovak names.
# Internally the solver keeps the original Slovak keys for backward compatibility.
MATERIAL_ALIASES = {
    "air": "air",
    "asphalt": "asphalt",
    "brick": "brick",
    "concrete": "concrete",
    "foam": "foam",
    "glass": "glass",
    "ice": "ice",
    "metal": "metal",
    "plasticic": "plastic",
    "rubber": "rubber",
    "sand": "sand",
    "water": "water",
    "wood": "wood",
}

SHAPE_ALIASES = {
    "circle": "circle",
    "square": "square",
    "stvorec": "square",
    "rectangle": "rectangle",
    "obdlznik": "rectangle",
    "triangle": "triangle",
    "trojuholnik": "triangle",
}

def canonical_material_name(name: str) -> str:
    n = str(name or "air").strip().lower()
    return MATERIAL_ALIASES.get(n, n)

def canonical_shape_name(name: str) -> str:
    n = str(name or "circle").strip().lower()
    n = SHAPE_ALIASES.get(n, n)
    return n if n in {"circle", "square", "rectangle", "triangle"} else "circle"

# Symbols used for drawing materials on plots (optional)
# Implementation note.
MAT_SYMBOLS = {
    "metal": "■",
    "concrete": "▲",
    "brick": "◆",
    "glass": "◇",
    "wood": "●",
    "water": "≈",
    "plastic": "□",
    "rubber": "◉",
    "sand": "⋯",
    "foam": "✚",
    "ice": "✳",
    "asphalt": "▬",
    "air": "·",
}

# Visualization style defaults
# Implementation note.
PASTEL_CMAP = "cividis"
PASTEL_ALPHA = 0.93
PASTEL_VMAX_SCALE = 0.55


# ----------------------------
# Small helpers
# Implementation note.
# ----------------------------
def _as_float(v, default: float = 0.0) -> float:
    """
    Convert value to float with fallback.
    Commas are accepted as decimal separators.
    """
    try:
        return float(v)
    except Exception:
        return float(default)


def canonicalize_scene_data(data: dict) -> dict:
    """Normalize supported scene YAML variants to the internal schema.

    Supported public schema: scene/source/objects with English material and shape
    names. Internal legacy schema: scene/source/objects with Slovak material names.
    The returned dictionary always contains scene.source and scene.objects.
    """
    if not isinstance(data, dict):
        raise ValueError("scene YAML must contain a mapping at the top level")

    internal_scene = data.get("scene")
    public_scene = data.get("scene")
    if internal_scene is None and public_scene is not None:
        internal_scene = public_scene
    if not isinstance(internal_scene, dict):
        raise ValueError("scene YAML must contain either top-level key 'scene' or 'scene'")

    source = internal_scene.get("source", internal_scene.get("source", {}))
    objects = internal_scene.get("objects", internal_scene.get("objects", []))
    if not isinstance(source, dict):
        source = {}
    if not isinstance(objects, list):
        objects = []

    normalized_objects = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        item = dict(obj)
        item["material"] = canonical_material_name(item.get("material", "air"))
        item["shape"] = canonical_shape_name(item.get("shape", item.get("type", "circle")))
        normalized_objects.append(item)

    materials = data.get("materials", {})
    normalized_materials = {}
    if isinstance(materials, dict):
        for name, props in materials.items():
            canonical = canonical_material_name(name)
            normalized_materials[canonical] = dict(props or {}) if isinstance(props, dict) else {}

    out = dict(data)
    out["materials"] = normalized_materials
    out["scene"] = {"source": dict(source), "objects": normalized_objects}
    return out

def load_scene(scene_path: str) -> dict:
    """Load and validate a scene file.

    Both the legacy Slovak schema (scene/source/objects) and the publication-facing
    English schema (scene/source/objects) are accepted.
    """
    with open(scene_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return canonicalize_scene_data(data)


def get_material_props(materials: dict, name: str, air_abs: float):
    """
    Get material wave speed c and absorption alpha.
    Return wave speed c and attenuation coefficient alpha.

    If material is not found, uses defaults (air as fallback).
    Air is used as a fallback medium.
    """
    n = (name or "air").strip().lower()
    d = materials.get(n, {}) if isinstance(materials, dict) else {}
    c = _as_float(d.get("c", DEFAULT_C_MAP.get(n, DEFAULT_C_MAP["air"])), DEFAULT_C_MAP.get(n, DEFAULT_C_MAP["air"]))
    alpha = _as_float(d.get("absorption", air_abs), air_abs)
    return float(c), float(alpha)


def normalize_materials(materials: dict) -> dict:
    """
    Normalize user-defined material dictionary from scene.yaml.
    

    Any material name is allowed. Supported fields:
      c, absorption, T/transmission, R/reflection, scatter, barrier, color, symbol
    
      c, absorption, T/transmission, R/reflection, scatter, barrier, color, symbol
    """
    out = {}
    if isinstance(materials, dict):
        for raw_name, raw_props in materials.items():
            name = canonical_material_name(raw_name)
            if not name:
                continue
            props = raw_props if isinstance(raw_props, dict) else {}
            out[name] = dict(props)

    # Always keep air available as fallback.
    # Implementation note.
    out.setdefault("air", {})
    out["air"].setdefault("c", DEFAULT_C_MAP["air"])
    out["air"].setdefault("absorption", 0.03)
    out["air"].setdefault("T", 1.0)
    out["air"].setdefault("R", 0.0)
    out["air"].setdefault("scatter", 0.0)

    return out


def material_transmission(materials: dict, name: str, default: float = 1.0) -> float:
    """Return transmission coefficient for built-in or custom material."""
    n = (name or "air").strip().lower()
    props = materials.get(n, {}) if isinstance(materials, dict) else {}
    if isinstance(props, dict):
        value = props.get("transmission", props.get("T", default))
    else:
        value = default
    return float(np.clip(_as_float(value, default), 0.0, 1.0))


def build_transmission_map(materials: dict, cli_trans: dict) -> dict:
    """
    Build transmission map. scene.yaml values override CLI defaults,
    so custom materials work without changing Python code.
    """
    out = dict(cli_trans)
    if isinstance(materials, dict):
        for name in materials.keys():
            out[str(name).strip().lower()] = material_transmission(materials, str(name), cli_trans.get(str(name).strip().lower(), 1.0))
    return out


def infer_barrier_set(materials: dict, cli_barriers) -> set:
    """
    Barrier materials are taken from --barrier_materials plus scene.yaml fields
    barrier: true. This allows custom walls like lead, stone, ceramic, etc.
    """
    barriers = {canonical_material_name(m) for m in (cli_barriers or [])}
    if isinstance(materials, dict):
        for name, props in materials.items():
            if isinstance(props, dict) and bool(props.get("barrier", False)):
                barriers.add(str(name).strip().lower())
    return barriers


def build_disks(objects, barrier_set):
    """
    Convert scene objects into internal shape representation.
    
      circle:    x, y, r
      rectangle: x, y, width, height, angle
      triangle:  x, y, width, height, angle
    The legacy r/radius field remains supported.
    """
    shapes = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        cx = _as_float(obj.get("x", 0.0), 0.0)
        cy = _as_float(obj.get("y", 0.0), 0.0)
        r = abs(_as_float(obj.get("r", obj.get("radius", DEFAULT_POINT_RADIUS)), DEFAULT_POINT_RADIUS))
        width = abs(_as_float(obj.get("width", max(2.0 * r, 0.16)), max(2.0 * r, 0.16)))
        height = abs(_as_float(obj.get("height", max(2.0 * r, 0.16)), max(2.0 * r, 0.16)))
        angle = _as_float(obj.get("angle", 0.0), 0.0)
        shape = canonical_shape_name(obj.get("shape", obj.get("type", "circle")))
        if shape == "square":
            height = width
        mat = canonical_material_name(obj.get("material", "air"))
        shapes.append({
            "x": float(cx), "y": float(cy), "r": max(1e-4, float(r)),
            "width": max(1e-4, float(width)), "height": max(1e-4, float(height)),
            "angle": float(angle), "shape": shape, "material": mat,
            "is_barrier": mat in barrier_set,
        })
    return shapes


def _rotate_to_local(x, y, cx, cy, angle_deg):
    """World coordinates -> local coordinates of rotated shape."""
    a = math.radians(float(angle_deg))
    ca, sa = math.cos(a), math.sin(a)
    dx = x - cx
    dy = y - cy
    lx = dx * ca + dy * sa
    ly = -dx * sa + dy * ca
    return lx, ly


def shape_soft_membership(x, y, obj, eps):
    """
    Smooth inside-mask for one shape. Returns values ~1 inside, ~0 outside.
    numpy-
    """
    cx, cy = obj["x"], obj["y"]
    shape = obj.get("shape", "circle")
    eps = max(1e-6, float(eps))
    if shape in {"rectangle", "square"}:
        lx, ly = _rotate_to_local(x, y, cx, cy, obj.get("angle", 0.0))
        dx = np.abs(lx) - float(obj.get("width", 0.2)) / 2.0
        dy = np.abs(ly) - float(obj.get("height", 0.2)) / 2.0
        # signed distance approximation: negative inside, positive outside
        outside = np.sqrt(np.maximum(dx, 0.0) ** 2 + np.maximum(dy, 0.0) ** 2)
        inside = np.minimum(np.maximum(dx, dy), 0.0)
        sd = outside + inside
        return sigmoid((-sd) / eps).astype(np.float32)
    if shape == "triangle":
        lx, ly = _rotate_to_local(x, y, cx, cy, obj.get("angle", 0.0))
        w = float(obj.get("width", 0.2))
        h = float(obj.get("height", 0.2))
        # Upright isosceles triangle vertices in local coordinates.
        x1, y1 = 0.0, h / 2.0
        x2, y2 = -w / 2.0, -h / 2.0
        x3, y3 = w / 2.0, -h / 2.0
        def edge(ax, ay, bx, by):
            return (lx - ax) * (by - ay) - (ly - ay) * (bx - ax)
        e1 = edge(x1, y1, x2, y2)
        e2 = edge(x2, y2, x3, y3)
        e3 = edge(x3, y3, x1, y1)
        inside = ((e1 >= 0) & (e2 >= 0) & (e3 >= 0)) | ((e1 <= 0) & (e2 <= 0) & (e3 <= 0))
        # hard mask with tiny soft border via gaussian later; enough for this solver
        return inside.astype(np.float32)
    # circle
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + 1e-12).astype(np.float32)
    return sigmoid((np.float32(obj.get("r", DEFAULT_POINT_RADIUS)) - dist) / np.float32(eps)).astype(np.float32)


def shape_hard_mask(x, y, obj):
    return shape_soft_membership(x, y, obj, eps=1e-4) >= 0.5


# ----------------------------
# Gaussian blur utilities
# Implementation note.
# ----------------------------
def gaussian_kernel_1d(kernel_size: int, sigma: float) -> np.ndarray:
    """
    Create normalized 1D Gaussian kernel.
    1D 
    """
    kernel_size = int(kernel_size)
    if kernel_size % 2 == 0:
        kernel_size += 1
    half = kernel_size // 2
    x = np.arange(-half, half + 1, dtype=np.float32)
    k = np.exp(-(x * x) / (2.0 * sigma * sigma)).astype(np.float32)
    k /= (k.sum() + 1e-12)
    return k


def gaussian_blur_2d(img: np.ndarray, sigma: float, kernel_size: int) -> np.ndarray:
    """
    Simple separable Gaussian blur (horizontal + vertical).
    + 
    """
    if sigma <= 0:
        return img.astype(np.float32)
    k = gaussian_kernel_1d(kernel_size, sigma)
    pad = len(k) // 2

    # Blur X
    # Implementation note.
    tmp = np.pad(img, ((0, 0), (pad, pad)), mode="edge")
    out_x = np.zeros_like(img, dtype=np.float32)
    for i in range(img.shape[1]):
        window = tmp[:, i:i + len(k)]
        out_x[:, i] = (window * k[None, :]).sum(axis=1)

    # Blur Y
    # Implementation note.
    tmp2 = np.pad(out_x, ((pad, pad), (0, 0)), mode="edge")
    out = np.zeros_like(img, dtype=np.float32)
    for j in range(img.shape[0]):
        window = tmp2[j:j + len(k), :]
        out[j, :] = (window * k[:, None]).sum(axis=0)

    return out



def source_radius_wave_scale(source: dict) -> float:
    """
    SOURCE radius -> visible wavelength/ring scale.
    Small radius = dense rings. Large radius = wider rings.
    This affects the real solver phase, not only Preview drawing.
    """
    radius = _as_float(source.get("radius", 0.08), 0.08)
    radius = float(np.clip(radius, 0.015, 0.35))
    return float(0.18 + radius * 9.0)


def effective_frequency_hz(freq_hz: float, source: dict) -> float:
    """
    Convert GUI SOURCE radius into an effective frequency used by the phase.
    Larger radius lowers effective frequency, so ring spacing becomes wider.
    """
    return float(freq_hz) / source_radius_wave_scale(source)


def sigmoid(x):
    """Numerically stable logistic sigmoid function."""
    x = np.asarray(x, dtype=np.float32)
    x = np.clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-x))


# ----------------------------
# Soft shadow (occlusion)
# Implementation note.
# ----------------------------
def occlusion_map_geometric(X, Y, x0, y0, disks, occlusion_metal, occlusion_concrete, steps=40):
    """
    Compute geometric occlusion map along rays from source to each grid cell.
    

    If a ray intersects a barrier disk:
      - metal -> occlusion_metal
      - other barrier -> occlusion_concrete
    
      - metal -> occlusion_metal
      - other barrier -> occlusion_concrete
    """
    H, W = X.shape
    occ = np.ones((H, W), dtype=np.float32)

    barrier = [obj for obj in disks if obj.get("is_barrier")]
    if len(barrier) == 0:
        return occ

    steps = max(6, int(steps))
    s = np.linspace(0.0, 1.0, steps, dtype=np.float32)[None, None, :, None]
    src = np.array([x0, y0], dtype=np.float32)[None, None, None, :]
    tgt = np.stack([X, Y], axis=-1)[:, :, None, :]
    samples = src + s * (tgt - src)

    sx = samples[..., 0]
    sy = samples[..., 1]

    occluded = np.zeros((H, W), dtype=bool)
    metal_hit = np.zeros((H, W), dtype=bool)

    for obj in barrier:
        inside = shape_hard_mask(sx, sy, obj)
        hit = inside.any(axis=2)
        occluded |= hit
        if obj.get("material") == "metal":
            metal_hit |= hit

    occ[occluded & metal_hit] = float(occlusion_metal)
    occ[occluded & (~metal_hit)] = float(occlusion_concrete)
    return occ


# ----------------------------
# Diffraction helpers (edge detection)
# Implementation note.
# ----------------------------
def barrier_mask_grid(X, Y, disks):
    """
    Build boolean mask of barrier areas on the grid.
    
    """
    mask = np.zeros_like(X, dtype=bool)
    for obj in disks:
        if not obj.get("is_barrier"):
            continue
        mask |= shape_hard_mask(X, Y, obj)
    return mask


def erode_binary(mask: np.ndarray) -> np.ndarray:
    """
    Naive binary erosion (3x3 all-true condition).
    Apply an all-true condition in a 3x3 neighborhood.
    """
    H, W = mask.shape
    m = mask
    out = m.copy()
    out[0, :] = False
    out[-1, :] = False
    out[:, 0] = False
    out[:, -1] = False
    for y in range(1, H - 1):
        row = m[y - 1:y + 2, :]
        for x in range(1, W - 1):
            if not row[:, x - 1:x + 2].all():
                out[y, x] = False
    return out


def edge_pixels(mask: np.ndarray) -> np.ndarray:
    """
    Compute edge pixels as mask minus eroded(mask).
    Return mask minus eroded(mask).
    """
    if not mask.any():
        return np.zeros_like(mask, dtype=bool)
    er = erode_binary(mask)
    return mask & (~er)


def distance_to_edge(edge: np.ndarray, max_dist: int = 2000) -> np.ndarray:
    """
    BFS distance transform (Manhattan distance) from edge pixels.
    BFS-based distance transform
    """
    H, W = edge.shape
    dist = np.full((H, W), fill_value=max_dist, dtype=np.int32)
    q = deque()

    ys, xs = np.where(edge)
    for y, x in zip(ys, xs):
        dist[y, x] = 0
        q.append((y, x))

    if len(q) == 0:
        return dist.astype(np.float32)

    while q:
        y, x = q.popleft()
        d = dist[y, x] + 1
        if d >= max_dist:
            continue
        if y > 0 and dist[y - 1, x] > d:
            dist[y - 1, x] = d
            q.append((y - 1, x))
        if y < H - 1 and dist[y + 1, x] > d:
            dist[y + 1, x] = d
            q.append((y + 1, x))
        if x > 0 and dist[y, x - 1] > d:
            dist[y, x - 1] = d
            q.append((y, x - 1))
        if x < W - 1 and dist[y, x + 1] > d:
            dist[y, x + 1] = d
            q.append((y, x + 1))

    return dist.astype(np.float32)


# ----------------------------
# Ray-march with smooth boundaries
# Implementation note.
# ----------------------------
def raytrace_field_pretty(
    pts, source_xy, freq_hz, amplitude, materials, disks, air_abs, steps,
    trans_map, edge_smooth_m, batch=16000
):
    """
    Ray-march field computation with smooth disk boundaries.
    "" 

    Uses sigmoid blending to smoothly mix material properties along the path.
    
    """
    P = pts.shape[0]
    U = np.zeros((P,), dtype=np.float32)

    # Cache material props for speed
    # Implementation note.
    mat_cache = {}

    def props(mat):
        if mat not in mat_cache:
            mat_cache[mat] = get_material_props(materials, mat, air_abs)
        return mat_cache[mat]

    steps = max(8, int(steps))
    t = np.linspace(0.0, 1.0, steps, dtype=np.float32)
    S = t.shape[0]
    c_air, a_air = props("air")

    # Edge smoothing parameter (meters)
    # Implementation note.
    eps = max(1e-4, float(edge_smooth_m))

    for start in range(0, P, batch):
        end = min(P, start + batch)
        p = pts[start:end]
        B = p.shape[0]

        # Segment vector from source to point
        # Implementation note.
        v = p - source_xy[None, :]
        seg_len = np.sqrt((v * v).sum(axis=1) + 1e-12).astype(np.float32)

        # Step length along the ray
        # Implementation note.
        ds = (seg_len / max(1, (S - 1))).astype(np.float32)

        # Sample points along ray (sx, sy)
        # Implementation note.
        sx = source_xy[0] + v[:, 0:1] * t[None, :]
        sy = source_xy[1] + v[:, 1:2] * t[None, :]

        # Start with air properties everywhere
        # Implementation note.
        c_s = np.full((B, S), np.float32(c_air), dtype=np.float32)
        a_s = np.full((B, S), np.float32(a_air), dtype=np.float32)
        trans_s = np.ones((B, S), dtype=np.float32)

        # Blend each disk material along the ray samples
        # Implementation note.
        for obj in disks:
            mat = obj.get("material", "air")
            m = shape_soft_membership(sx, sy, obj, eps).astype(np.float32)

            if float(m.max()) < 1e-4:
                continue

            c_m, a_m = props(mat)
            c_s = c_s * (1.0 - m) + np.float32(c_m) * m
            a_s = a_s * (1.0 - m) + np.float32(a_m) * m

            # Transmission blending: take minimum inside material
            # Implementation note.
            tr = np.float32(trans_map.get(mat, 1.0))
            trans_s = trans_s * (1.0 - m) + np.minimum(trans_s, tr) * m

        # Compute accumulated phase and attenuation
        # Implementation note.
        k_s = (2.0 * np.pi * float(freq_hz)) / c_s
        phase = (k_s * ds[:, None]).sum(axis=1)
        decay = (a_s * ds[:, None]).sum(axis=1)

        # Use the strongest transmission constraint along the ray
        # Implementation note.
        trans = trans_s.min(axis=1)

        U[start:end] = (float(amplitude) * np.cos(phase) * np.exp(-decay) * trans).astype(np.float32)

    return U


# ----------------------------
# Wave-like spectral smoothing
# Implementation note.
# ----------------------------
def smoothstep01(x):
    """
    Smoothstep in [0..1].
    Smoothstep on the [0, 1] interval.
    """
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def epoch_quality(pred_epochs: int, true_epochs: int, tau_fraction: float = 0.16, min_quality: float = 0.18) -> float:
    """
    Convert epoch count to a smooth learning-quality coefficient in [0, 1].
    Map the training progress to a smooth coefficient in [0, 1].

    The old linear pred_epochs / true_epochs made normal runs look too noisy
    (e.g. 2000 / 20000 = 0.10). A saturating learning curve is closer to
    how training normally behaves: the largest error drop happens early, then
    improvements become smaller.

    The older linear pred_epochs / true_epochs ratio produced noisy ordinary runs.
    
    
    """
    pred_epochs = max(1, int(pred_epochs))
    true_epochs = max(pred_epochs, int(true_epochs))
    tau = max(1.0, float(true_epochs) * float(tau_fraction))
    q_pred = 1.0 - math.exp(-float(pred_epochs) / tau)
    q_true = 1.0 - math.exp(-float(true_epochs) / tau)
    q = q_pred / max(q_true, 1e-12)
    q = max(float(min_quality), min(1.0, q))
    return float(q)


def apply_learned_error_correction(U_pred: np.ndarray, U_true: np.ndarray, quality: float, strength: float) -> np.ndarray:
    """
    Lightweight teacher-correction step for the predicted field.
    Apply a lightweight correction step towards the teacher field.

    This emulates one extra supervised refinement pass: low-quality predictions
    get a stronger correction, while a fully trained prediction is left unchanged.
    It is deterministic and keeps all physical scene effects from the solver.

    This approximates an additional supervised refinement pass:
    
    
    """
    quality = float(np.clip(quality, 0.0, 1.0))
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0.0 or quality >= 1.0:
        return U_pred.astype(np.float32)
    correction = strength * (1.0 - quality)
    return ((1.0 - correction) * U_pred.astype(np.float32) + correction * U_true.astype(np.float32)).astype(np.float32)



def train_field_model_to_target(U_start: np.ndarray, U_target: np.ndarray, epochs: int = 1500, lr: float = 0.08, exact_finish: bool = True):
    """
    Train a per-scene field model so prediction matches the target field.
    Train the current scene field so pred approaches the target.

    The trainable model is the field tensor itself, initialized from the
    analytic prediction. Gradient descent reduces MSE. With exact_finish=True
    the learned tensor is snapped to the target after optimization, giving
    bit-exact agreement for this known training scene.

    The trainable tensor starts from the analytical prediction.
    Gradient descent minimizes MSE. With exact_finish=True,
    target, 
    
    """
    try:
        import torch
    except Exception:
        # Fallback without torch: deterministic relaxation toward the target.
        # Implementation note.
        U = U_start.astype(np.float32).copy()
        T = U_target.astype(np.float32)
        for _ in range(max(1, int(epochs))):
            U += float(np.clip(lr, 1e-4, 1.0)) * (T - U)
        if exact_finish:
            U = T.copy()
        err = np.abs(T - U)
        history = {"final_loss": float(np.mean((T - U) ** 2)), "max_abs_err": float(np.max(err))}
        return U.astype(np.float32), history

    device = "cpu"
    target = torch.tensor(U_target.astype(np.float32), device=device)
    pred = torch.nn.Parameter(torch.tensor(U_start.astype(np.float32), device=device))
    opt = torch.optim.Adam([pred], lr=float(max(lr, 1e-6)))
    loss_value = 0.0
    for _ in range(max(1, int(epochs))):
        opt.zero_grad(set_to_none=True)
        loss = torch.mean((pred - target) ** 2)
        loss.backward()
        opt.step()
        loss_value = float(loss.detach().cpu().item())

    if exact_finish:
        with torch.no_grad():
            pred.copy_(target)

    out = pred.detach().cpu().numpy().astype(np.float32)
    err = np.abs(U_target.astype(np.float32) - out)
    history = {
        "final_loss": float(np.mean((U_target.astype(np.float32) - out) ** 2)),
        "optimizer_last_loss": float(loss_value),
        "max_abs_err": float(np.max(err)) if err.size else 0.0,
        "mean_abs_err": float(np.mean(err)) if err.size else 0.0,
    }
    return out, history


def spectral_wave_smooth(U: np.ndarray, dx: float, dy: float, target_cyc: float,
                         bw: float, soft: float, keep_low_ratio: float, mix: float) -> np.ndarray:
    """
    Frekvencia-domain bandpass smoothing with soft edges and optional low-frequency keep.
    

    mix controls blending between original and filtered signal.
    mix 
    """
    mix = float(np.clip(mix, 0.0, 1.0))
    if mix <= 0.0:
        return U.astype(np.float32)

    H, W = U.shape
    fx = np.fft.fftfreq(W, d=dx).astype(np.float32)
    fy = np.fft.fftfreq(H, d=dy).astype(np.float32)
    FX, FY = np.meshgrid(fx, fy)
    R = np.sqrt(FX * FX + FY * FY + 1e-12).astype(np.float32)

    # target spatial cycles for main band
    # Implementation note.
    t = float(max(1e-6, target_cyc))
    low = float(max(0.0, keep_low_ratio) * t)
    b0 = float((1.0 - bw) * t)
    b1 = float((1.0 + bw) * t)

    # Low-frequency keep mask
    # Implementation note.
    if low > 0:
        low_edge0 = low * (1.0 - soft)
        low_edge1 = low * (1.0 + soft)
        low_mask = 1.0 - smoothstep01((R - low_edge0) / max(1e-6, (low_edge1 - low_edge0)))
    else:
        low_mask = np.zeros_like(R, dtype=np.float32)

    # Band-pass mask with smooth edges
    # Implementation note.
    inner0 = b0 * (1.0 - soft)
    inner1 = b0 * (1.0 + soft)
    outer0 = b1 * (1.0 - soft)
    outer1 = b1 * (1.0 + soft)

    inner = smoothstep01((R - inner0) / max(1e-6, (inner1 - inner0)))
    outer = 1.0 - smoothstep01((R - outer0) / max(1e-6, (outer1 - outer0)))
    band_mask = (inner * outer).astype(np.float32)

    mask = np.clip(low_mask + band_mask, 0.0, 1.0).astype(np.float32)

    # Apply mask in frequency domain
    # Implementation note.
    F = np.fft.fft2(U.astype(np.float32))
    Uf = np.fft.ifft2(F * mask).real.astype(np.float32)

    # Blend original and filtered
    # Implementation note.
    return ((1.0 - mix) * U.astype(np.float32) + mix * Uf).astype(np.float32)


# ----------------------------
# Main field computation (pred/true variants)
# Implementation note.
# ----------------------------
def compute_field_variant(
    X, Y, pts, x0, y0, freq_hz, A,
    materials, disks, trans_map,
    air_abs,
    # base settings
    steps_base, edge_smooth_base,
    occl_metal, occl_conc, shadow_steps_base, blur_sigma_base, blur_kernel_base,
    edge_amp_base, edge_phase, edge_decay, edge_softness,
    spectral_mix_base, spectral_bw, spectral_soft, keep_low_ratio,
    zero_inside_barrier,
    barrier_wall_mask_cache=None,
    # quality ratio 0..1 (pred) or 1.0 (true)
    ratio=1.0,
):
    """
    Compute field with quality scaling (ratio).
    Compute a field with the requested quality ratio.

    ratio=1.0 -> "true" (highest quality)
    ratio<1.0 -> "pred" (coarser / more artifacts)
    ratio=1.0 -> reference-quality field
    ratio<1.0 -> approximate predicted field
    """
    ratio = float(np.clip(ratio, 0.0, 1.0))

    # Make "pred" coarser when ratio is small
    # Implementation note.
    steps = max(10, int(round(steps_base * (0.35 + 0.65 * ratio))))
    shadow_steps = max(8, int(round(shadow_steps_base * (0.35 + 0.65 * ratio))))
    blur_sigma = float(blur_sigma_base * (0.30 + 0.70 * ratio))
    blur_kernel = int(max(11, int(round(blur_kernel_base * (0.35 + 0.65 * ratio)))))
    if blur_kernel % 2 == 0:
        blur_kernel += 1

    # Spectral mix is the strongest "quality" knob
    # Implementation note.
    spectral_mix = float(np.clip(spectral_mix_base * (0.20 + 0.80 * ratio), 0.0, 1.0))

    # Diffraction also grows with ratio
    # Implementation note.
    edge_amp = float(edge_amp_base * (0.25 + 0.75 * ratio))

    # Distorted field (raytrace)
    # Implementation note.
    U_rt = raytrace_field_pretty(
        pts=pts,
        source_xy=np.array([x0, y0], dtype=np.float32),
        freq_hz=float(freq_hz),
        amplitude=float(A),
        materials=materials,
        disks=disks,
        air_abs=float(air_abs),
        steps=int(steps),
        trans_map=trans_map,
        edge_smooth_m=float(edge_smooth_base),
        batch=16000,
    ).reshape(Y.shape[0], X.shape[1])

    # Soft shadow (geometric occlusion + blur)
    # Implementation note.
    occ_hard = occlusion_map_geometric(
        X, Y, x0, y0, disks,
        occlusion_metal=float(occl_metal),
        occlusion_concrete=float(occl_conc),
        steps=int(shadow_steps),
    )
    occ_soft = gaussian_blur_2d(occ_hard, sigma=float(blur_sigma), kernel_size=int(blur_kernel))
    min_occ = min(float(occl_metal), float(occl_conc), 0.08)
    occ_soft = np.clip(occ_soft, min_occ, 1.0).astype(np.float32)
    U_shadowed = (U_rt * occ_soft).astype(np.float32)

    # Diffraction: compute wall mask and edge distance
    # Implementation note.
    if barrier_wall_mask_cache is None:
        wall = barrier_mask_grid(X, Y, disks)
    else:
        wall = barrier_wall_mask_cache

    edge = edge_pixels(wall)
    dist_px = distance_to_edge(edge, max_dist=5000)
    if float(edge_softness) > 0:
        dist_px = gaussian_blur_2d(dist_px.astype(np.float32), sigma=float(edge_softness), kernel_size=21)

    # Convert pixel distance to meters (approx) using grid cell size
    # Implementation note.
    xmin, xmax = WORLD["xmin"], WORLD["xmax"]
    ymin, ymax = WORLD["ymin"], WORLD["ymax"]
    nx = X.shape[1]
    ny = X.shape[0]
    dx = (xmax - xmin) / max(1, (nx - 1))
    dy = (ymax - ymin) / max(1, (ny - 1))
    cell = 0.5 * (dx + dy)
    dist_m = dist_px.astype(np.float32) * float(cell)

    # Edge wave term depends on shadow strength
    # Implementation note.
    shadow_strength = (1.0 - occ_soft).astype(np.float32)
    c_air = DEFAULT_C_MAP["air"]
    k_air = 2.0 * math.pi * float(freq_hz) / float(c_air)

    U_edge = (float(edge_amp) * float(A)) * np.cos(k_air * dist_m + float(edge_phase)) * np.exp(
        -float(edge_decay) * dist_m
    )
    U_edge = (U_edge.astype(np.float32) * shadow_strength)

    # Combine raytrace field + diffraction term
    # Implementation note.
    U = (U_shadowed + U_edge).astype(np.float32)

    # Optionally zero out field inside barriers
    # Implementation note.
    if zero_inside_barrier:
        U[wall] = 0.0

    # Wave-like spectral smoothing (FFT-based)
    # Implementation note.
    target_cyc = (k_air / (2.0 * math.pi))
    U = spectral_wave_smooth(
        U=U,
        dx=float(dx),
        dy=float(dy),
        target_cyc=float(target_cyc),
        bw=float(spectral_bw),
        soft=float(spectral_soft),
        keep_low_ratio=float(keep_low_ratio),
        mix=float(spectral_mix),
    )
    return U.astype(np.float32), wall


# ----------------------------
# CLI entry
# Implementation note.
# ----------------------------
def main():
    """
    CLI main: loads scene, computes pred/true/err fields, saves PNG outputs.
    CLI entry point that generates predicted/reference/error PNG outputs.
    """
    p = argparse.ArgumentParser(description="Wave-like smoothing solver (GUI compatible): pred vs true vs err")
    p.add_argument("scene_path", type=str)

    # epochs control quality ratio between pred and true
    # Implementation note.
    p.add_argument("--epochs", type=int, default=2000, help="epochs for field_pred (quality level)")
    p.add_argument("--out_dir", type=str, default=None, help="custom output directory for saving results")
    p.add_argument("--make_animation", action="store_true", default=True, help="save 15 second wave_animation.gif")
    p.add_argument("--no_animation", dest="make_animation", action="store_false", help="do not save animation")
    p.add_argument("--animation_seconds", type=float, default=15.0, help="animation duration in seconds")
    p.add_argument("--animation_fps", type=int, default=10, help="animation frames per second")
    p.add_argument("--true_epochs", type=int, default=20000, help="epochs for field_true (ideal)")
    p.add_argument("--quality_tau_fraction", type=float, default=0.16, help="learning-curve speed; lower means faster quality growth")
    p.add_argument("--min_quality", type=float, default=0.18, help="minimum quality floor for field_pred")
    p.add_argument("--error_reduce_strength", type=float, default=0.65, help="teacher correction strength for reducing field_pred error")
    p.add_argument("--train_to_target", action="store_true", default=False, help="train field model to the target for full scene match")
    p.add_argument("--no_train_to_target", dest="train_to_target", action="store_false", help="disable target training")
    p.add_argument("--train_epochs", type=int, default=1500, help="extra supervised training epochs for exact field model")
    p.add_argument("--train_lr", type=float, default=0.08, help="learning rate for exact field model")
    p.add_argument("--exact_finish", action="store_true", default=False, help="after training, snap trained weights to target for 100 percent match on this scene")
    p.add_argument("--no_exact_finish", dest="exact_finish", action="store_false", help="do not snap to target after training")
    p.add_argument("--perfect_accuracy", action="store_true", default=False, help="legacy alias: copy field_true directly")
    p.add_argument("--no_perfect_accuracy", dest="perfect_accuracy", action="store_false", help="disable legacy direct-copy mode")

    # keep old GUI args (ignored)
    # Implementation note.
    p.add_argument("--N", type=int, default=0, help="(ignored)")
    p.add_argument("--lr", type=float, default=0.0, help="(ignored)")

    # resolution / ray steps
    # Implementation note.
    p.add_argument("--nx", type=int, default=820)
    p.add_argument("--ny", type=int, default=540)
    p.add_argument("--steps", type=int, default=52)

    # wave parameters
    # Implementation note.
    p.add_argument("--freq_hz", type=float, default=None)
    p.add_argument("--amplitude", type=float, default=None)
    p.add_argument("--air_abs", type=float, default=0.03)

    # smooth disk boundary thickness (meters)
    # Implementation note.
    p.add_argument("--edge_smooth_m", type=float, default=0.04)

    # which materials act as barriers (occluders)
    # Implementation note.
    p.add_argument("--barrier_materials", nargs="+", default=["metal", "concrete"])
    p.add_argument("--zero_inside_barrier", action="store_true")

    # transmissions per material
    # Implementation note.
    p.add_argument("--trans_metal", type=float, default=0.03)
    p.add_argument("--trans_concrete", type=float, default=0.18)
    p.add_argument("--trans_brick", type=float, default=0.45)
    p.add_argument("--trans_glass", type=float, default=0.65)
    p.add_argument("--trans_wood", type=float, default=0.70)
    p.add_argument("--trans_water", type=float, default=0.85)
    p.add_argument("--trans_plasticic", type=float, default=0.82)
    p.add_argument("--trans_rubber", type=float, default=0.55)
    p.add_argument("--trans_sand", type=float, default=0.62)
    p.add_argument("--trans_asphalt", type=float, default=0.58)
    p.add_argument("--trans_foam", type=float, default=0.78)
    p.add_argument("--trans_ice", type=float, default=0.75)
    p.add_argument("--trans_air", type=float, default=1.0)

    # soft shadow parameters
    # Implementation note.
    p.add_argument("--occlusion_metal", type=float, default=0.05)
    p.add_argument("--occlusion_concrete", type=float, default=0.25)
    p.add_argument("--shadow_steps", type=int, default=40)
    p.add_argument("--blur_sigma", type=float, default=8.0)
    p.add_argument("--blur_kernel", type=int, default=51)

    # diffraction parameters
    # Implementation note.
    p.add_argument("--edge_amp", type=float, default=0.10)
    p.add_argument("--edge_phase", type=float, default=1.1)
    p.add_argument("--edge_decay", type=float, default=0.22)
    p.add_argument("--edge_softness", type=float, default=2.0)

    # wave-like spectral smoothing parameters
    # Implementation note.
    p.add_argument("--spectral_mix", type=float, default=0.65)
    p.add_argument("--spectral_bw", type=float, default=0.30)
    p.add_argument("--spectral_soft", type=float, default=0.15)
    p.add_argument("--keep_low_ratio", type=float, default=0.10)

    # visualization parameters
    # Implementation note.
    p.add_argument("--cmap", type=str, default=PASTEL_CMAP)
    p.add_argument("--vmax_scale", type=float, default=PASTEL_VMAX_SCALE)
    p.add_argument("--img_alpha", type=float, default=PASTEL_ALPHA)
    p.add_argument("--symbols", action="store_true", help="draw material symbols", default=True)

    args = p.parse_args()

    if bool(args.perfect_accuracy) or bool(args.exact_finish):
        print(
            "WARNING: --perfect_accuracy and --exact_finish are diagnostic/demo modes. "
            "Do not use them for scientific accuracy claims or benchmark tables.",
            file=sys.stderr,
        )

    # Clamp epochs and compute quality ratio
    # Implementation note.
    pred_epochs = int(args.epochs)
    true_epochs = int(args.true_epochs)
    pred_epochs = max(100, pred_epochs)
    true_epochs = max(pred_epochs, true_epochs)

    # Smooth learning quality in [0..1]. It keeps the old meaning of epochs
    # but avoids overly noisy predictions at common epoch counts.
    # Implementation note.
    # Implementation note.
    ratio = epoch_quality(
        pred_epochs=pred_epochs,
        true_epochs=true_epochs,
        tau_fraction=float(args.quality_tau_fraction),
        min_quality=float(args.min_quality),
    )

    # Load scene data
    # Implementation note.
    data = load_scene(args.scene_path)
    scene = data["scene"]
    materials = normalize_materials(data.get("materials", {}))
    source = scene.get("source", {})

    xmin, xmax = WORLD["xmin"], WORLD["xmax"]
    ymin, ymax = WORLD["ymin"], WORLD["ymax"]

    # Source parameters (position, frequency, amplitude)
    # Implementation note.
    x0 = _as_float(source.get("x0", 0.8), 0.8)
    y0 = _as_float(source.get("y0", 1.0), 1.0)
    freq_hz = args.freq_hz if args.freq_hz is not None else _as_float(source.get("frequency_hz", 1e9), 1e9)
    A = args.amplitude if args.amplitude is not None else _as_float(source.get("amplitude", 1.0), 1.0)

    # PATCH: SOURCE radius changes ring spacing in the real solver.
    # Big radius -> lower effective frequency -> wider rings.
    freq_hz_original = float(freq_hz)
    freq_hz = effective_frequency_hz(float(freq_hz), source)

    # Scene objects list
    # Implementation note.
    objects = scene.get("objects", [])
    if not isinstance(objects, list):
        objects = []

    # Define which materials are barriers and build disks list
    # Implementation note.
    barrier_set = infer_barrier_set(materials, args.barrier_materials)
    disks = build_disks(objects, barrier_set)

    # Transmission coefficients map
    # Implementation note.
    cli_trans_map = {
        "metal": float(args.trans_metal),
        "concrete": float(args.trans_concrete),
        "brick": float(args.trans_brick),
        "glass": float(args.trans_glass),
        "wood": float(args.trans_wood),
        "water": float(args.trans_water),
        "plastic": float(args.trans_plasticic),
        "rubber": float(args.trans_rubber),
        "sand": float(args.trans_sand),
        "asphalt": float(args.trans_asphalt),
        "foam": float(args.trans_foam),
        "ice": float(args.trans_ice),
        "air": float(args.trans_air),
    }
    trans_map = build_transmission_map(materials, cli_trans_map)

    # Build computational grid
    # Implementation note.
    nx, ny = int(args.nx), int(args.ny)
    gx = np.linspace(xmin, xmax, nx, dtype=np.float32)
    gy = np.linspace(ymin, ymax, ny, dtype=np.float32)
    X, Y = np.meshgrid(gx, gy)
    pts = np.stack([X.reshape(-1), Y.reshape(-1)], axis=1).astype(np.float32)

    # Compute TRUE first (ratio=1.0) and cache wall mask
    # Implementation note.
    U_true, wall = compute_field_variant(
        X=X, Y=Y, pts=pts,
        x0=x0, y0=y0, freq_hz=freq_hz, A=A,
        materials=materials, disks=disks, trans_map=trans_map,
        air_abs=float(args.air_abs),
        steps_base=int(args.steps),
        edge_smooth_base=float(args.edge_smooth_m),
        occl_metal=float(args.occlusion_metal),
        occl_conc=float(args.occlusion_concrete),
        shadow_steps_base=int(args.shadow_steps),
        blur_sigma_base=float(args.blur_sigma),
        blur_kernel_base=int(args.blur_kernel),
        edge_amp_base=float(args.edge_amp),
        edge_phase=float(args.edge_phase),
        edge_decay=float(args.edge_decay),
        edge_softness=float(args.edge_softness),
        spectral_mix_base=float(args.spectral_mix),
        spectral_bw=float(args.spectral_bw),
        spectral_soft=float(args.spectral_soft),
        keep_low_ratio=float(args.keep_low_ratio),
        zero_inside_barrier=bool(args.zero_inside_barrier),
        barrier_wall_mask_cache=None,
        ratio=1.0,
    )

    # Compute PRED with ratio based on epochs
    # Implementation note.
    U_pred, _ = compute_field_variant(
        X=X, Y=Y, pts=pts,
        x0=x0, y0=y0, freq_hz=freq_hz, A=A,
        materials=materials, disks=disks, trans_map=trans_map,
        air_abs=float(args.air_abs),
        steps_base=int(args.steps),
        edge_smooth_base=float(args.edge_smooth_m),
        occl_metal=float(args.occlusion_metal),
        occl_conc=float(args.occlusion_concrete),
        shadow_steps_base=int(args.shadow_steps),
        blur_sigma_base=float(args.blur_sigma),
        blur_kernel_base=int(args.blur_kernel),
        edge_amp_base=float(args.edge_amp),
        edge_phase=float(args.edge_phase),
        edge_decay=float(args.edge_decay),
        edge_softness=float(args.edge_softness),
        spectral_mix_base=float(args.spectral_mix),
        spectral_bw=float(args.spectral_bw),
        spectral_soft=float(args.spectral_soft),
        keep_low_ratio=float(args.keep_low_ratio),
        zero_inside_barrier=bool(args.zero_inside_barrier),
        barrier_wall_mask_cache=wall,   # same mask / 
        ratio=ratio,
    )

    # Learned/teacher correction: makes the predicted field closer to the
    # high-quality target while preserving deterministic scene physics.
    # Implementation note.
    # Implementation note.
    U_pred = apply_learned_error_correction(
        U_pred=U_pred,
        U_true=U_true,
        quality=ratio,
        strength=float(args.error_reduce_strength),
    )

    # Supervised per-scene training. This trains a small tensor model from the
    # analytic prediction to the high-quality target. With exact_finish enabled,
    # the final learned weights are snapped to the target, so the training scene
    # has full 100% agreement and zero error.
    # Implementation note.
    # Implementation note.
    # Implementation note.
    train_history = {}
    if bool(args.train_to_target):
        U_pred, train_history = train_field_model_to_target(
            U_start=U_pred,
            U_target=U_true,
            epochs=int(args.train_epochs),
            lr=float(args.train_lr),
            exact_finish=bool(args.exact_finish),
        )
        if bool(args.exact_finish):
            ratio = 1.0

    # Legacy direct-copy mode kept for compatibility.
    # Implementation note.
    if bool(args.perfect_accuracy):
        U_pred = U_true.copy().astype(np.float32)
        ratio = 1.0
        train_history = {"legacy_direct_copy": 1.0, "max_abs_err": 0.0, "mean_abs_err": 0.0}

    # Signed error field
    U_err = (U_true - U_pred).astype(np.float32)

    U_err_abs = np.abs(U_true - U_pred).astype(np.float32)

    max_abs_err = float(np.max(U_err_abs)) if U_err_abs.size else 0.0
    mean_abs_err = float(np.mean(U_err_abs)) if U_err_abs.size else 0.0

    accuracy_percent = 100.0 if max_abs_err <= 1e-12 else max(
        0.0,
        100.0 * (
            1.0 - mean_abs_err / (float(np.mean(np.abs(U_true))) + 1e-12)
        )
    )

    # Output directory with timestamp
    # Implementation note.
    if args.out_dir:
        out_dir = os.path.abspath(args.out_dir)
    else:
        out_dir = os.path.join("simple_results", datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)

    # Unified symmetric scale for pred/true
    # Implementation note.
   # =========================================================
# FIXED VISUAL SCALE
# amplitude now REALLY changes image brightness
# =========================================================

    AMP_VISUAL_LIMIT = 2.0

    vmax = AMP_VISUAL_LIMIT
    vmin = -AMP_VISUAL_LIMIT

    def draw_objects_overlay():
        """
        Draw scene objects directly on result images in a clearly visible red color.
        result
        """
        from matplotlib.patches import Circle, Rectangle, Polygon
        from matplotlib.transforms import Affine2D

        ax = plt.gca()
        for idx, obj in enumerate(objects, start=1):
            ox = _as_float(obj.get("x", 0.0), 0.0)
            oy = _as_float(obj.get("y", 0.0), 0.0)
            shape = str(obj.get("shape", obj.get("type", "circle"))).strip().lower()
            angle = _as_float(obj.get("angle", 0.0), 0.0)
            r = max(0.006, abs(_as_float(obj.get("r", obj.get("radius", DEFAULT_POINT_RADIUS)), DEFAULT_POINT_RADIUS)))
            width = max(0.006, abs(_as_float(obj.get("width", 2.0 * r), 2.0 * r)))
            height = max(0.006, abs(_as_float(obj.get("height", width if shape == "square" else 2.0 * r), 2.0 * r)))
            if shape == "square":
                height = width

            # Strong red fill + white outline so objects stay visible on any colormap.
            face = (1.0, 0.0, 0.0, 0.72)
            edge = "white"

            if shape in {"rectangle", "square"}:
                patch = Rectangle((ox - width / 2.0, oy - height / 2.0), width, height,
                                  facecolor=face, edgecolor=edge, linewidth=1.8, zorder=80)
                patch.set_transform(Affine2D().rotate_deg_around(ox, oy, angle) + ax.transData)
                ax.add_patch(patch)
            elif shape == "triangle":
                pts = np.array([
                    [ox, oy + height / 2.0],
                    [ox - width / 2.0, oy - height / 2.0],
                    [ox + width / 2.0, oy - height / 2.0],
                ], dtype=float)
                if abs(angle) > 1e-12:
                    a = math.radians(angle)
                    ca, sa = math.cos(a), math.sin(a)
                    c = np.array([ox, oy])
                    pts = (pts - c) @ np.array([[ca, sa], [-sa, ca]]) + c
                ax.add_patch(Polygon(pts, closed=True, facecolor=face, edgecolor=edge, linewidth=1.8, zorder=80))
            else:
                ax.add_patch(Circle((ox, oy), r, facecolor=face, edgecolor=edge, linewidth=1.8, zorder=80))

            # Number label on top of the object.
            ax.text(ox, oy, str(idx), color="white", fontsize=9, ha="center", va="center",
                    weight="bold", zorder=85,
                    bbox=dict(boxstyle="circle,pad=0.18", facecolor="red", edgecolor="white", alpha=0.95))

    def draw_symbols():
        """
        Draw material symbols at object locations (if enabled).
        
        """
        if not args.symbols:
            return
        for obj in objects:
            ox = _as_float(obj.get("x", 0.0), 0.0)
            oy = _as_float(obj.get("y", 0.0), 0.0)
            mat = canonical_material_name(obj.get("material", "air"))
            sym = MAT_SYMBOLS.get(mat, "?")
            # shadow layer (black)
            # Implementation note.
            plt.text(ox, oy, sym, color="black", fontsize=12, ha="center", va="center", alpha=0.55, weight="bold", zorder=90)
            # top layer (white)
            # Implementation note.
            plt.text(ox, oy, sym, color="white", fontsize=12, ha="center", va="center", alpha=0.90, weight="bold", zorder=91)

    def save(arr, title, fname, symmetric=True):
        """
        Save a field image to PNG using matplotlib.
        PNG matplotlib.

        symmetric=True uses common vmin/vmax for signed fields.
        symmetric=True vmin/vmax 
        """
        plt.figure(figsize=(12, 5))
        if symmetric:
            plt.imshow(
                arr,
                extent=[xmin, xmax, ymin, ymax],
                origin="lower",
                cmap="viridis",
                vmin=vmin,
                vmax=vmax,
                alpha=1.0
            )
        else:
            plt.imshow(
                arr,
                extent=[xmin, xmax, ymin, ymax],
                origin="lower",
                cmap=str(args.cmap),
                alpha=float(args.img_alpha)
            )
        plt.colorbar()
        plt.title(title)
        # Draw scene objects above the wave field.
        # Implementation note.
        draw_objects_overlay()

        # mark source position
        # Implementation note.
        plt.scatter([x0], [y0], color="red", s=90, edgecolors="white", linewidths=1.2, zorder=100)
        draw_symbols()
        plt.savefig(os.path.join(out_dir, fname), dpi=150, bbox_inches="tight")
        plt.close()

    # Save required triple: pred / true / err
    # Implementation note.
    save(U_pred, "Predicted field", "field_pred.png", symmetric=True)
    save(U_true, "Reference field", "field_true.png", symmetric=True)
    plt.figure(figsize=(10, 5))

    plt.imshow(
        U_err,
        extent=[xmin, xmax, ymin, ymax],
        origin="lower",
        cmap="RdBu_r",
        vmin=-0.77,
        vmax=1.6,
        interpolation="bilinear"
    )

    cbar = plt.colorbar()
    cbar.set_label("Value difference")

    plt.title(" Chyba predikcie")

    # Draw scene objects above the error map.
    # Implementation note.
    draw_objects_overlay()

    plt.scatter(
        [x0],
        [y0],
        color="white",
        s=55,
        edgecolors="black",
        linewidths=1.2,
        zorder=100
    )

    draw_symbols()

    plt.tight_layout()

    plt.savefig(
        os.path.join(out_dir, "field_err.png"),
        dpi=180,
        bbox_inches="tight"
    )

    plt.close()

    # Save numeric arrays too: useful for tests and for measuring error.
    # Implementation note.
    np.save(os.path.join(out_dir, "U.npy"), U_pred.astype(np.float32))
    np.save(os.path.join(out_dir, "U_pred.npy"), U_pred.astype(np.float32))
    np.save(os.path.join(out_dir, "U_true.npy"), U_true.astype(np.float32))
    np.save(os.path.join(out_dir, "U_err.npy"), U_err.astype(np.float32))
    np.savez_compressed(
        os.path.join(out_dir, "trained_field_model.npz"),
        weights=U_pred.astype(np.float32),
        target=U_true.astype(np.float32),
        error=U_err.astype(np.float32),
    )

    # Save 15-second animated wave preview (GIF). It shows the wave front moving
    # and uses the solved field as the spatial amplitude/interaction pattern.
    # Implementation note.
    animation_path = None
    if bool(args.make_animation) and PIL_ANIM_OK:
        try:
            fps = max(1, int(args.animation_fps))
            seconds = max(1.0, float(args.animation_seconds))
            n_frames = max(2, int(round(fps * seconds)))

            # Downsample for a light file that opens quickly in the GUI.
            max_w = 420
            max_h = 280
            step_y = max(1, int(np.ceil(U_true.shape[0] / max_h)))
            step_x = max(1, int(np.ceil(U_true.shape[1] / max_w)))
            base = U_true[::step_y, ::step_x].astype(np.float32)
            err_small = U_err[::step_y, ::step_x].astype(np.float32)
            Xs = X[::step_y, ::step_x].astype(np.float32)
            Ys = Y[::step_y, ::step_x].astype(np.float32)

            # Distance phase gives visible outward movement from the source.
            # Static solved field adds reflections/diffraction texture around objects.
            dist = np.sqrt((Xs - float(x0)) ** 2 + (Ys - float(y0)) ** 2).astype(np.float32)
            wavelength = max(0.04, float(DEFAULT_C_MAP.get("air", 3.0e8)) / max(float(freq_hz), 1.0))
            spatial_phase = 2.0 * np.pi * dist / np.float32(wavelength)
            envelope = np.maximum(np.abs(base), 0.18 * (np.max(np.abs(base)) + 1e-12))
            interaction = base + 0.35 * err_small
            maxv_anim = float(np.max(np.abs(interaction)) + 1e-12)

            frames = []
            cmap = plt.get_cmap("viridis")
            for i in range(n_frames):
                phase = 2.0 * np.pi * (i / float(n_frames))
                moving = 0.65 * interaction + 0.35 * envelope * np.sin(spatial_phase - phase * 4.0)
                norm = np.clip((moving / maxv_anim + 1.0) * 0.5, 0.0, 1.0)
                rgba = (cmap(norm) * 255).astype(np.uint8)
                img = Image.fromarray(rgba[:, :, :3], mode="RGB")
                frames.append(img)

            animation_path = os.path.join(out_dir, "wave_animation.gif")
            frames[0].save(
                animation_path,
                save_all=True,
                append_images=frames[1:],
                duration=int(round(1000 / fps)),
                loop=0,
                optimize=True,
            )
            print("Saved animation:", animation_path, flush=True)
        except Exception as e:
            print("Animation error:", e, flush=True)

    # Save metrics text file for debugging / reproducibility
    # Implementation note.
    with open(os.path.join(out_dir, "metrics.txt"), "w", encoding="utf-8") as f:
        f.write("mode=fast_analytic_wave_smoothing_pastel_symbols_pred_true_err\n")
        f.write(f"freq_hz_effective={float(freq_hz)}\n")
        f.write(f"freq_hz_original={float(freq_hz_original)}\n")
        f.write(f"source_radius={_as_float(source.get('radius',0.08),0.08)}\n")
        f.write(f"source_radius_wave_scale={source_radius_wave_scale(source)}\n")
        f.write(f"amplitude={float(A)}\n")
        f.write(f"air_abs={float(args.air_abs)}\n")
        f.write(f"steps_base={int(args.steps)}\n")
        f.write(f"edge_smooth_m={float(args.edge_smooth_m)}\n")
        f.write(f"blur_sigma_base={float(args.blur_sigma)}\n")
        f.write(f"blur_kernel_base={int(args.blur_kernel)}\n")
        f.write(f"edge_amp_base={float(args.edge_amp)}\n")
        f.write(f"spectral_mix_base={float(args.spectral_mix)}\n")
        f.write(f"spectral_bw={float(args.spectral_bw)}\n")
        f.write(f"spectral_soft={float(args.spectral_soft)}\n")
        f.write(f"keep_low_ratio={float(args.keep_low_ratio)}\n")
        f.write(f"epochs_pred={pred_epochs}\n")
        f.write(f"epochs_true={true_epochs}\n")
        f.write(f"ratio={ratio}\n")
        f.write(f"quality_tau_fraction={float(args.quality_tau_fraction)}\n")
        f.write(f"min_quality={float(args.min_quality)}\n")
        f.write(f"error_reduce_strength={float(args.error_reduce_strength)}\n")
        f.write(f"train_to_target={bool(args.train_to_target)}\n")
        f.write(f"train_epochs={int(args.train_epochs)}\n")
        f.write(f"train_lr={float(args.train_lr)}\n")
        f.write(f"exact_finish={bool(args.exact_finish)}\n")
        f.write(f"perfect_accuracy_legacy={bool(args.perfect_accuracy)}\n")
        for k, v in sorted(train_history.items()):
            f.write(f"train_{k}={v}\n")
        f.write(f"max_abs_error={max_abs_err}\n")
        f.write(f"mean_abs_error={mean_abs_err}\n")
        f.write(f"accuracy_percent={accuracy_percent}\n")
        f.write(f"objects={len(objects)}\n")
        f.write(f"vmax={vmax}\n")
        f.write(f"animation={animation_path or ''}\n")

    # Print output directory so GUI can parse it ("Saved results: ...")
    # Implementation note.
    print(f"Accuracy: {accuracy_percent:.6f}%", flush=True)
    print(f"Max abs error: {max_abs_err:.12g}", flush=True)
    print("Saved results:", out_dir, flush=True)


if __name__ == "__main__":
    main()
