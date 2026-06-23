#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys
import yaml

WORLD = dict(xmin=0.0, xmax=3.0, ymin=0.0, ymax=2.0)

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
    "rectangle": "rectangle",
    "triangle": "triangle",
    "stvorec": "square",
    "obdlznik": "rectangle",
    "trojuholnik": "triangle",
}

def canonical_material_name(name: str) -> str:
    n = str(name or "air").strip().lower()
    return MATERIAL_ALIASES.get(n, n)

def canonical_shape_name(name: str) -> str:
    n = str(name or "circle").strip().lower()
    n = SHAPE_ALIASES.get(n, n)
    return n if n in {"circle", "square", "rectangle", "triangle"} else "circle"

DEFAULT_MATERIALS = {
    "air":      {"absorption": 0.03, "c": 3.0e8, "T": 1.00, "R": 0.00, "scatter": 0.00, "barrier": False},
    "asphalt":  {"absorption": 0.06, "c": 2.2e8, "T": 0.58, "R": 0.50, "scatter": 0.40, "barrier": False},
    "brick":    {"absorption": 0.07, "c": 2.0e8, "T": 0.45, "R": 0.55, "scatter": 0.50, "barrier": False},
    "concrete": {"absorption": 0.08, "c": 2.0e8, "T": 0.18, "R": 0.60, "scatter": 0.55, "barrier": True},
    "foam":     {"absorption": 0.05, "c": 1.3e8, "T": 0.78, "R": 0.10, "scatter": 0.08, "barrier": False},
    "glass":    {"absorption": 0.05, "c": 2.2e8, "T": 0.65, "R": 0.15, "scatter": 0.25, "barrier": False},
    "ice":      {"absorption": 0.02, "c": 3.1e8, "T": 0.75, "R": 0.08, "scatter": 0.12, "barrier": False},
    "metal":    {"absorption": 0.10, "c": 2.5e8, "T": 0.03, "R": 0.90, "scatter": 1.00, "barrier": True},
    "plastic":  {"absorption": 0.05, "c": 2.4e8, "T": 0.82, "R": 0.10, "scatter": 0.18, "barrier": False},
    "rubber":   {"absorption": 0.09, "c": 1.6e8, "T": 0.55, "R": 0.25, "scatter": 0.20, "barrier": False},
    "sand":     {"absorption": 0.08, "c": 1.7e8, "T": 0.62, "R": 0.35, "scatter": 0.45, "barrier": False},
    "water":    {"absorption": 0.06, "c": 1.5e8, "T": 0.85, "R": 0.10, "scatter": 0.25, "barrier": False},
    "wood":     {"absorption": 0.06, "c": 2.0e8, "T": 0.70, "R": 0.30, "scatter": 0.35, "barrier": False},
}

def die(msg: str):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(1)

def fnum(x: str) -> float:
    # strict float parse
    try:
        return float(x)
    except Exception:
        die(f"not a number: {x}")

def in_range(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def load_scene(path: Path) -> dict:
    if not path.exists():
        # init default scene
        return {
            "materials": DEFAULT_MATERIALS,
            "scene": {
                "source": {"x0": 0.8, "y0": 1.0, "frequency_hz": 1e9, "amplitude": 1.0},
                "objects": []
            }
        }
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    scene = data.get("scene", data.get("scene"))
    if not isinstance(scene, dict):
        die("scene file missing top-level key: scene or scene")

    source = scene.get("source", scene.get("source", {"x0": 0.8, "y0": 1.0, "frequency_hz": 1e9, "amplitude": 1.0}))
    objects = scene.get("objects", scene.get("objects", []))
    if not isinstance(source, dict):
        source = {"x0": 0.8, "y0": 1.0, "frequency_hz": 1e9, "amplitude": 1.0}
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

    materials = dict(DEFAULT_MATERIALS)
    user_materials = data.get("materials", {})
    if isinstance(user_materials, dict):
        for name, props in user_materials.items():
            materials[canonical_material_name(name)] = dict(props or {}) if isinstance(props, dict) else {}

    return {"materials": materials, "scene": {"source": dict(source), "objects": normalized_objects}}

def save_scene(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def list_objects(data: dict):
    objs = data["scene"]["objects"]
    if not objs:
        print("(no objects)")
        return
    for i, o in enumerate(objs):
        x = o.get("x", 0.0)
        y = o.get("y", 0.0)
        r = o.get("r", 0.08)
        m = o.get("material", "air")
        shape = o.get("shape", "circle")
        width = o.get("width", 2 * r)
        height = o.get("height", 2 * r)
        angle = o.get("angle", 0.0)
        print(f"{i:02d}: x={x:.4f} y={y:.4f} shape={shape} r={r:.4f} width={width:.4f} height={height:.4f} angle={angle:.1f} material={m}")

def known_materials(data: dict) -> dict:
    mats = dict(DEFAULT_MATERIALS)
    user_mats = data.get("materials", {})
    if isinstance(user_mats, dict):
        for k, v in user_mats.items():
            if str(k).strip():
                mats[canonical_material_name(k)] = dict(v or {}) if isinstance(v, dict) else {}
    data["materials"] = mats
    return mats

def list_materials(data: dict):
    mats = known_materials(data)
    for name in sorted(mats.keys()):
        props = mats[name]
        print(
            f"{name}: c={props.get('c', 'auto')} "
            f"absorption={props.get('absorption', 'auto')} "
            f"T={props.get('T', props.get('transmission', 'auto'))} "
            f"R={props.get('R', props.get('reflection', 'auto'))} "
            f"scatter={props.get('scatter', 'auto')} "
            f"barrier={bool(props.get('barrier', False))}"
        )

def add_material(data: dict, name: str, c: float, absorption: float, T: float, R: float, scatter: float, barrier: bool):
    name = canonical_material_name(name)
    if not name:
        die("material name is empty")
    mats = known_materials(data)
    mats[name] = {
        "c": float(c),
        "absorption": float(absorption),
        "T": in_range(float(T), 0.0, 1.0),
        "R": in_range(float(R), 0.0, 1.0),
        "scatter": in_range(float(scatter), 0.0, 1.0),
        "barrier": bool(barrier),
    }

def delete_material(data: dict, name: str):
    name = canonical_material_name(name)
    mats = known_materials(data)
    if name == "air":
        die("air material cannot be deleted")
    if name not in mats:
        die(f"unknown material: {name}")
    for o in data["scene"].get("objects", []):
        if str(o.get("material", "")).strip().lower() == name:
            die(f"material {name} is used by an object; change/delete that object first")
    del mats[name]

def add_object(data: dict, x: float, y: float, material: str, r: float, shape: str, width: float, height: float, angle: float):
    material = canonical_material_name(material)
    mats = known_materials(data)
    if material not in mats:
        die(f"unknown material: {material}. Allowed: {', '.join(sorted(mats.keys()))}")
    x = in_range(x, WORLD["xmin"], WORLD["xmax"])
    y = in_range(y, WORLD["ymin"], WORLD["ymax"])
    r = abs(r)
    shape = canonical_shape_name(shape)
    if shape not in {"circle", "square", "rectangle", "triangle"}:
        die("shape must be: circle, square, rectangle, triangle")
    width = abs(width) if width is not None else max(2.0 * r, 0.16)
    height = abs(height) if height is not None else max(2.0 * r, 0.16)
    data["scene"]["objects"].append({
        "x": x, "y": y, "r": r, "width": width, "height": height,
        "angle": float(angle), "shape": shape, "material": material,
    })

def delete_object(data: dict, idx: int):
    objs = data["scene"]["objects"]
    if idx < 0 or idx >= len(objs):
        die(f"bad index {idx}. Use: list")
    del objs[idx]

def update_object(data: dict, idx: int, x, y, material, r, shape=None, width=None, height=None, angle=None):
    objs = data["scene"]["objects"]
    if idx < 0 or idx >= len(objs):
        die(f"bad index {idx}. Use: list")
    o = objs[idx]
    if x is not None: o["x"] = in_range(x, WORLD["xmin"], WORLD["xmax"])
    if y is not None: o["y"] = in_range(y, WORLD["ymin"], WORLD["ymax"])
    if r is not None: o["r"] = abs(r)
    if width is not None: o["width"] = abs(width)
    if height is not None: o["height"] = abs(height)
    if angle is not None: o["angle"] = float(angle)
    if shape is not None:
        shape = canonical_shape_name(shape)
        if shape not in {"circle", "square", "rectangle", "triangle"}:
            die("shape must be: circle, square, rectangle, triangle")
        o["shape"] = shape
    if material is not None:
        material = canonical_material_name(material)
        mats = known_materials(data)
        if material not in mats:
            die(f"unknown material: {material}. Allowed: {', '.join(sorted(mats.keys()))}")
        o["material"] = material

def set_source(data: dict, x0, y0, freq, amp):
    s = data["scene"]["source"]
    if x0 is not None: s["x0"] = in_range(x0, WORLD["xmin"], WORLD["xmax"])
    if y0 is not None: s["y0"] = in_range(y0, WORLD["ymin"], WORLD["ymax"])
    if freq is not None: s["frequency_hz"] = float(freq)
    if amp is not None: s["amplitude"] = float(amp)

def main():
    ap = argparse.ArgumentParser(description="No-GUI scene editor for scene.yaml")
    ap.add_argument("--scene", dest="scene_file", default="scene.yaml", help="path to scene YAML file")

    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list objects")
    sub.add_parser("materials", help="list available materials")

    ma = sub.add_parser("material-add", help="add/update custom material")
    ma.add_argument("name")
    ma.add_argument("--c", required=True, help="wave speed, for example 2.1e8")
    ma.add_argument("--absorption", required=True)
    ma.add_argument("--T", default="0.7", help="transmission 0..1")
    ma.add_argument("--R", default="0.3", help="reflection 0..1")
    ma.add_argument("--scatter", default="0.2", help="scatter 0..1")
    ma.add_argument("--barrier", action="store_true", help="treat as wall/occluder")

    md = sub.add_parser("material-del", help="delete custom material")
    md.add_argument("name")

    a = sub.add_parser("add", help="add object")
    a.add_argument("--x", required=True)
    a.add_argument("--y", required=True)
    a.add_argument("--material", required=True)
    a.add_argument("--shape", default="circle", choices=["circle", "square", "rectangle", "triangle", "circle", "square", "rectangle", "triangle"])
    a.add_argument("--r", default="0.08", help="circle radius / fallback size")
    a.add_argument("--width", default="0.16", help="rectangle/triangle width")
    a.add_argument("--height", default="0.16", help="rectangle/triangle height")
    a.add_argument("--angle", default="0", help="rotation angle in degrees")

    d = sub.add_parser("del", help="delete object by index")
    d.add_argument("index", type=int)

    u = sub.add_parser("update", help="update object by index")
    u.add_argument("index", type=int)
    u.add_argument("--x")
    u.add_argument("--y")
    u.add_argument("--material")
    u.add_argument("--r")
    u.add_argument("--shape", choices=["circle", "square", "rectangle", "triangle", "circle", "square", "rectangle", "triangle"])
    u.add_argument("--width")
    u.add_argument("--height")
    u.add_argument("--angle")

    s = sub.add_parser("source", help="set source parameters")
    s.add_argument("--x0")
    s.add_argument("--y0")
    s.add_argument("--freq")
    s.add_argument("--amp")

    args = ap.parse_args()
    scene_path = Path(args.scene_file)

    data = load_scene(scene_path)

    if args.cmd == "list":
        list_objects(data)
        return

    if args.cmd == "materials":
        list_materials(data)
        return

    if args.cmd == "material-add":
        add_material(
            data, args.name,
            c=fnum(args.c), absorption=fnum(args.absorption),
            T=fnum(args.T), R=fnum(args.R), scatter=fnum(args.scatter),
            barrier=bool(args.barrier),
        )
        save_scene(scene_path, data)
        print("OK material saved. Now available materials:")
        list_materials(data)
        return

    if args.cmd == "material-del":
        delete_material(data, args.name)
        save_scene(scene_path, data)
        print("OK material deleted. Now available materials:")
        list_materials(data)
        return

    if args.cmd == "add":
        add_object(
            data,
            x=fnum(args.x),
            y=fnum(args.y),
            material=args.material,
            r=fnum(args.r),
            shape=args.shape,
            width=fnum(args.width),
            height=fnum(args.height),
            angle=fnum(args.angle),
        )
        save_scene(scene_path, data)
        print("OK added. Now:")
        list_objects(data)
        return

    if args.cmd == "del":
        delete_object(data, args.index)
        save_scene(scene_path, data)
        print("OK deleted. Now:")
        list_objects(data)
        return

    if args.cmd == "update":
        update_object(
            data, args.index,
            x=fnum(args.x) if args.x is not None else None,
            y=fnum(args.y) if args.y is not None else None,
            material=args.material,
            r=fnum(args.r) if args.r is not None else None,
            shape=args.shape,
            width=fnum(args.width) if args.width is not None else None,
            height=fnum(args.height) if args.height is not None else None,
            angle=fnum(args.angle) if args.angle is not None else None,
        )
        save_scene(scene_path, data)
        print("OK updated. Now:")
        list_objects(data)
        return

    if args.cmd == "source":
        set_source(
            data,
            x0=fnum(args.x0) if args.x0 is not None else None,
            y0=fnum(args.y0) if args.y0 is not None else None,
            freq=fnum(args.freq) if args.freq is not None else None,
            amp=fnum(args.amp) if args.amp is not None else None,
        )
        save_scene(scene_path, data)
        print("OK source updated:", data["scene"]["source"])
        return

if __name__ == "__main__":
    main()
