"""Bundle the whole project into one self-contained page: showcase.html

    python tools/build_showcase.py

Embeds the 3D meshes (quantised), printable STLs, demo video, a render, the phone control
page and config.h, so showcase.html works on its own (only three.js loads from a CDN).
Re-run after changing the CAD, firmware config or control page.
"""
import base64
import glob
import io
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad")


def read_stl(path):
    """Binary STL -> flat list of vertex coordinates (9 floats per triangle)."""
    b = open(path, "rb").read()
    n = struct.unpack_from("<I", b, 80)[0]
    out = []
    for i in range(n):
        off = 84 + i * 50 + 12  # skip the facet normal
        out.extend(struct.unpack_from("<9f", b, off))
    return out


def quantise(coords):
    """Store coordinates as uint16 inside the part's bounding box (~0.005 mm steps)."""
    xs, ys, zs = coords[0::3], coords[1::3], coords[2::3]
    lo = [min(xs), min(ys), min(zs)]
    hi = [max(xs), max(ys), max(zs)]
    span = [max(h - l, 1e-6) for l, h in zip(lo, hi)]
    q = bytearray()
    for i, v in enumerate(coords):
        a = i % 3
        q += struct.pack("<H", round((v - lo[a]) / span[a] * 65535))
    return {"min": lo, "span": span, "tris": len(coords) // 9, "data": base64.b64encode(bytes(q)).decode()}


def b64file(path):
    return base64.b64encode(open(path, "rb").read()).decode()


def jpeg_b64(path, width=1600, quality=82):
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=quality, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        return "data:image/png;base64," + b64file(path)


def script_json(obj):
    """JSON that is safe inside a <script> element."""
    return json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")


def main():
    manifest = json.load(open(os.path.join(CAD, "blender", "manifest.json")))
    for p in manifest["parts"]:
        p["mesh"] = quantise(read_stl(os.path.join(CAD, "blender", p["file"])))

    printable = {}
    for f in sorted(glob.glob(os.path.join(CAD, "stl", "*.stl"))):
        printable[os.path.splitext(os.path.basename(f))[0]] = quantise(read_stl(f))

    data = {
        "manifest": manifest,
        "printable": printable,
        "appHtml": open(os.path.join(ROOT, "ui", "index.html"), encoding="utf-8").read(),
        "configH": open(os.path.join(ROOT, "firmware", "VacController", "config.h"), encoding="utf-8").read(),
    }
    video = os.path.join(CAD, "blender", "render", "vaccontroller_demo.mp4")
    render = os.path.join(CAD, "blender", "render", "exploded.png")

    tpl = open(os.path.join(ROOT, "tools", "showcase_template.html"), encoding="utf-8").read()
    html = (tpl.replace("__DATA_JSON__", script_json(data))
               .replace("__VIDEO_SRC__", "data:video/mp4;base64," + b64file(video) if os.path.exists(video) else "")
               .replace("__RENDER_SRC__", jpeg_b64(render) if os.path.exists(render) else ""))
    out = os.path.join(ROOT, "showcase.html")
    open(out, "w", encoding="utf-8").write(html)
    tris = sum(p["mesh"]["tris"] for p in manifest["parts"])
    print(f"wrote {out}: {os.path.getsize(out) / 1e6:.1f} MB, {len(manifest['parts'])} parts, {tris} triangles")


main()
