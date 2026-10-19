"""Render PNG previews of the CAD output with matplotlib (no GUI needed).

    "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" cad/render_previews.py
Writes cad/previews/{printed_parts,assembly,exploded}.png
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import Mesh
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "previews")
os.makedirs(OUT, exist_ok=True)
LIGHT = np.array([0.35, -0.55, 0.75])
LIGHT /= np.linalg.norm(LIGHT)


def load(path):
    m = Mesh.Mesh(path)
    pts, tris = m.Topology
    return np.array([[p.x, p.y, p.z] for p in pts]), np.array(tris)


def shade(verts, tris, rgb):
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    n = np.cross(b - a, c - a)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    k = 0.35 + 0.65 * np.clip(n @ LIGHT, 0, 1)
    return np.clip(np.outer(k, rgb), 0, 1)


def draw(ax, meshes, elev=28, azim=-58):
    # One collection for everything: matplotlib depth-sorts per collection, then per face inside it.
    allpts, faces, colours = [], [], []
    for verts, tris, rgb, off in meshes:
        v = verts + off
        faces.append(v[tris])
        colours.append(shade(v, tris, rgb))
        allpts.append(v)
    ax.add_collection3d(Poly3DCollection(np.concatenate(faces), facecolors=np.concatenate(colours),
                                         edgecolor="none", linewidth=0))
    p = np.vstack(allpts)
    lo, hi = p.min(0), p.max(0)
    mid, span = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(mid[0] - span, mid[0] + span)
    ax.set_ylim(mid[1] - span, mid[1] + span)
    ax.set_zlim(mid[2] - span, mid[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


# Printed parts, one panel each.
names = ["base", "lid", "pump_cradle", "valve_bracket", "electronics_plate", "hose_grommet", "cylinder_stand"]
fig = plt.figure(figsize=(16, 9), dpi=110)
for i, n in enumerate(names):
    ax = fig.add_subplot(2, 4, i + 1, projection="3d")
    v, t = load(os.path.join(HERE, "stl", n + ".stl"))
    draw(ax, [(v, t, np.array([0.9, 0.42, 0.15]), 0)], elev=35 if n != "base" else 50)
    ax.set_title(n, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "printed_parts.png"))
plt.close(fig)

# Assembly views from the Blender manifest (parts in place).
man = json.load(open(os.path.join(HERE, "blender", "manifest.json")))
parts = [(p, *load(os.path.join(HERE, "blender", p["file"]))) for p in man["parts"] if p["name"] != "cylinder_stand"]
for name, exploded, hide_lid in [("assembly", False, False), ("assembly_open", False, True), ("exploded", True, False)]:
    fig = plt.figure(figsize=(10, 8), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    ms = []
    for p, v, t in parts:
        if hide_lid and p["explode"][2] >= 90:  # the lid and everything mounted in it
            continue
        off = np.array(p["explode"]) * 1.4 if exploded else 0
        ms.append((v, t, np.array(p["color"]) * 0.85 + 0.1, off))
    draw(ax, ms, elev=32 if not hide_lid else 55, azim=-58)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name + ".png"))
    plt.close(fig)
print("previews written to", OUT)
