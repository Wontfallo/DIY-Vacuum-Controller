"""Parametric CAD for the VacController enclosure and printed parts (FreeCAD 1.x).

Run headless:
    "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" cad/build_cad.py

Change the numbers in PARAMETERS to match the parts you actually bought, then re-run.
Outputs (next to this file):
    VacController.FCStd        full model: printed parts + placeholder "bought" parts, assembled
    step/*.step                each printed part, plus the whole assembly
    stl/*.stl                  printed parts, already in print orientation
    blender/parts/*.stl        every part in its assembled position, for the Blender demo
    blender/manifest.json      names, colours, groups and explode offsets for the Blender demo
"""
import json
import math
import os

import FreeCAD as App
import Import
import MeshPart
import Part
from FreeCAD import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))

# =============================== PARAMETERS (mm) ===============================
W, D, H = 180.0, 130.0, 75.0      # enclosure base outside size (lid sits on top)
WALL, FLOOR, R = 2.4, 3.0, 6.0    # wall, floor, corner radius
LID_T, LIP_H, CLEAR = 3.0, 4.0, 0.3
BOSS_D, INSERT_D, INSERT_DEPTH = 9.0, 4.2, 8.0   # M3 heat-set inserts in the corner bosses
LID_SCREW_D, LID_CBORE_D, LID_CBORE_DEPTH = 3.4, 6.5, 1.8
GRID_PITCH, GRID_HOLE_D = 10.0, 2.8               # floor mounting grid (M3 self-tapping)

# Panel cut-outs. Measure your parts; these suit the common AliExpress versions.
GAUGE_HOLE_D = 40.5      # 40 mm panel vacuum gauge
STOP_HOLE_D = 16.2       # 16 mm momentary push button
ROCKER_CUT = (19.2, 13.2)  # KCD1 rocker switch
LED_HOLE_D = 5.2
DC_JACK_D = 11.0         # DC-022 panel barrel jack
USB_SLOT = (13.0, 8.0)
HOSE_PORT_D = 10.0       # takes the printed TPU grommet
RELIEF_VALVE_D = 13.0
EXHAUST_D = 6.0

PUMP_D, PUMP_LEN, PAD = 28.0, 75.0, 1.5   # pump motor diameter / overall length / foam pad
TUBE_OD = 6.0
PERF = (70.0, 50.0, 66.0, 46.0)           # perfboard size and mounting-hole spacing
CYL_D = 62.0                              # outside diameter of the bought cylinder

# Layout inside the box (x along W, y along D; front wall is y = 0).
PUMP_POS = (18.0, 34.0)       # left end of pump, axis y
VALVE_POS = (112.0, 30.0)
PLATE_POS = (12.0, 66.0)      # electronics plate corner
GAUGE_POS = (55.0, 72.0)      # on the lid
STOP_POS = (138.0, 88.0)
ROCKER_POS = (138.0, 46.0)
LED_POS = (138.0, 66.0)
# ===============================================================================


def rbox(w, d, h, r, x=0.0, y=0.0, z=0.0):
    b = Part.makeBox(w, d, h, V(x, y, z))
    if r > 0:
        vertical = [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) > 1e-6]
        b = b.makeFillet(r, vertical)
    return b


def cyl(r, h, x, y, z, d=V(0, 0, 1)):
    return Part.makeCylinder(r, h, V(x, y, z), d)


def cut_all(shape, cutters):
    return shape.cut(Part.makeCompound(cutters)) if cutters else shape


def perfboard_origin():
    """Corner of the perfboard (it sits on the electronics plate's standoffs) and its top z."""
    return PLATE_POS[0] + 15, PLATE_POS[1] + 5, FLOOR + 2.5 + 6 + 1.6


def esp32_usb_yz():
    bx, by, bz = perfboard_origin()
    return by + 22 + 14, bz + 9


def boss_xy():
    o = WALL + BOSS_D / 2
    return [(o, o), (W - o, o), (o, D - o), (W - o, D - o)]


def engrave(text, size, x, y, z, depth):
    """Text cutter (Arial Bold), centred on (x, y), from z downwards. None if fonts are missing."""
    try:
        chars = Part.makeWireString(text, "C:/Windows/Fonts/", "arialbd.ttf", size, 0)
        faces = [Part.makeFace(ws, "Part::FaceMakerBullseye") for ws in chars if ws]
        solid = Part.makeCompound([f.extrude(V(0, 0, depth)) for f in faces])
        bb = solid.BoundBox
        solid.translate(V(x - (bb.XMin + bb.XMax) / 2, y - (bb.YMin + bb.YMax) / 2, z - depth))
        return solid
    except Exception as e:  # engraving is cosmetic
        print("engrave skipped:", e)
        return None


# ------------------------------------------------------------------ printed parts

def make_base():
    outer = rbox(W, D, H, R)
    inner = rbox(W - 2 * WALL, D - 2 * WALL, H, R - WALL, WALL, WALL, FLOOR)
    base = outer.cut(inner)
    for x, y in boss_xy():
        base = base.fuse(cyl(BOSS_D / 2, H - FLOOR, x, y, FLOOR))
    cut = [cyl(INSERT_D / 2, INSERT_DEPTH + 0.1, x, y, H - INSERT_DEPTH) for x, y in boss_xy()]

    # Mounting grid through the floor, clear of the corner bosses.
    gx = int((W - 30) // GRID_PITCH)
    gy = int((D - 30) // GRID_PITCH)
    x0 = (W - (gx - 1) * GRID_PITCH) / 2
    y0 = (D - (gy - 1) * GRID_PITCH) / 2
    for i in range(gx):
        for j in range(gy):
            cut.append(cyl(GRID_HOLE_D / 2, FLOOR + 0.2, x0 + i * GRID_PITCH, y0 + j * GRID_PITCH, -0.1))

    # Front wall (y = 0): hose port by the valve.
    cut.append(cyl(HOSE_PORT_D / 2, WALL + 0.2, 150, -0.1, FLOOR + 22, V(0, 1, 0)))
    # Left wall (x = 0): USB slot lined up with the ESP32's USB end. Back wall (y = D): DC jack.
    usb_y, usb_z = esp32_usb_yz()
    cut.append(Part.makeBox(WALL + 0.2, USB_SLOT[0], USB_SLOT[1], V(-0.1, usb_y - USB_SLOT[0] / 2, usb_z - USB_SLOT[1] / 2)))
    cut.append(cyl(DC_JACK_D / 2, WALL + 0.2, 145, D - WALL - 0.1, 35, V(0, 1, 0)))
    # Right wall (x = W): relief valve and vent-valve exhaust.
    cut.append(cyl(RELIEF_VALVE_D / 2, WALL + 0.2, W - WALL - 0.1, 40, 40, V(1, 0, 0)))
    cut.append(cyl(EXHAUST_D / 2, WALL + 0.2, W - WALL - 0.1, 70, 22, V(1, 0, 0)))
    # Vent slots: left wall by the pump, right wall up high.
    for k in range(6):
        cut.append(Part.makeBox(WALL + 0.2, 2.5, 26, V(-0.1, 22 + k * 7, 18)))
        cut.append(Part.makeBox(WALL + 0.2, 2.5, 18, V(W - WALL - 0.1, 86 + k * 6, 45)))
    # Recesses for 12 mm stick-on rubber feet.
    for x, y in [(18, 18), (W - 18, 18), (18, D - 18), (W - 18, D - 18)]:
        cut.append(cyl(6.3, 1.0, x, y, -0.01))
    return cut_all(base, cut)


def make_lid():
    """Modelled in assembled position: underside at z = H."""
    top = rbox(W, D, LID_T, R, 0, 0, H)
    iw, idd = W - 2 * WALL - 2 * CLEAR, D - 2 * WALL - 2 * CLEAR
    lip = rbox(iw, idd, LIP_H, R - WALL, WALL + CLEAR, WALL + CLEAR, H - LIP_H)
    lip = lip.cut(rbox(iw - 3.2, idd - 3.2, LIP_H, max(R - WALL - 1.6, 0.5), WALL + CLEAR + 1.6, WALL + CLEAR + 1.6, H - LIP_H))
    lip = cut_all(lip, [cyl(BOSS_D / 2 + 0.6, LIP_H, x, y, H - LIP_H) for x, y in boss_xy()])
    lid = top.fuse(lip)
    zt = H + LID_T
    cut = []
    for x, y in boss_xy():
        cut.append(cyl(LID_SCREW_D / 2, LID_T + 0.2, x, y, H - 0.1))
        cut.append(cyl(LID_CBORE_D / 2, LID_CBORE_DEPTH + 0.1, x, y, zt - LID_CBORE_DEPTH))
    cut.append(cyl(GAUGE_HOLE_D / 2, LID_T + 0.2, GAUGE_POS[0], GAUGE_POS[1], H - 0.1))
    cut.append(cyl(STOP_HOLE_D / 2, LID_T + 0.2, STOP_POS[0], STOP_POS[1], H - 0.1))
    cut.append(cyl(LED_HOLE_D / 2, LID_T + 0.2, LED_POS[0], LED_POS[1], H - 0.1))
    rw, rh = ROCKER_CUT
    cut.append(Part.makeBox(rw, rh, LID_T + 0.2, V(ROCKER_POS[0] - rw / 2, ROCKER_POS[1] - rh / 2, H - 0.1)))
    for text, size, x, y in [("STOP", 5, STOP_POS[0], STOP_POS[1] + 15), ("POWER", 4, ROCKER_POS[0], ROCKER_POS[1] - 13),
                             ("RUN", 3.2, LED_POS[0] + 10, LED_POS[1]), ("VACUUM", 4, GAUGE_POS[0], GAUGE_POS[1] - 27)]:
        t = engrave(text, size, x, y, zt + 0.01, 0.6)
        if t:
            cut.append(t)
    return cut_all(lid, cut)


def make_pump_cradle():
    """One saddle; print two. Modelled at the origin, pump axis along X."""
    t, base_t = 14.0, 3.0
    rad = PUMP_D / 2 + PAD
    wc = PUMP_D + 12
    seat_z = base_t + 4 + rad
    body = Part.makeBox(t, wc, seat_z, V(0, -wc / 2, 0))
    body = body.fuse(Part.makeBox(t, wc + 20, base_t, V(0, -(wc + 20) / 2, 0)))
    cut = [cyl(rad, t + 0.2, -0.1, 0, seat_z, V(1, 0, 0))]
    # Zip-tie tunnel under the seat, and M3 slots in the flanges for the floor grid.
    cut.append(Part.makeBox(5, wc + 0.2, 2.2, V(t / 2 - 2.5, -wc / 2 - 0.1, base_t + 0.8)))
    for s in (-1, 1):
        cy = s * (wc / 2 + 5)
        slot = Part.makeBox(3.4, 3.4, base_t + 0.2, V(t / 2 - 1.7, cy - 1.7, -0.1))
        slot = slot.fuse(cyl(1.7, base_t + 0.2, t / 2, cy - 1.7, -0.1)).fuse(cyl(1.7, base_t + 0.2, t / 2, cy + 1.7, -0.1))
        cut.append(slot)
    return cut_all(body, cut), seat_z


def make_valve_bracket():
    base = Part.makeBox(34, 26, 3)
    wall = Part.makeBox(34, 3, 26, V(0, 0, 0))
    b = base.fuse(wall)
    cut = [Part.makeBox(5, 3.2, 2.4, V(x, -0.1, 14)) for x in (6, 23)]   # zip-tie slots
    cut += [Part.makeBox(3.4, 10, 3.2, V(x, 12, -0.1)) for x in (5, 25.6)]  # floor-grid slots
    return cut_all(b, cut)


def make_electronics_plate():
    pw, pd, pt = 100.0, 60.0, 2.5
    p = rbox(pw, pd, pt, 3)
    ox, oy = (pw - PERF[2]) / 2, (pd - PERF[3]) / 2
    for i in (0, 1):
        for j in (0, 1):
            p = p.fuse(cyl(2.6, 6, ox + i * PERF[2], oy + j * PERF[3], pt))
    cut = [cyl(1.1, 9, ox + i * PERF[2], oy + j * PERF[3], 0.5) for i in (0, 1) for j in (0, 1)]
    for x, y in [(5, 5), (pw - 5, 5), (5, pd - 5), (pw - 5, pd - 5)]:
        slot = Part.makeBox(12, 3.4, pt + 0.2, V(x - 6, y - 1.7, -0.1))
        cut.append(slot)
    return cut_all(p, cut)


def make_grommet():
    """Print in TPU. Pushes into the hose port; the tube passes through snugly."""
    g = cyl(8, 1.5, 0, 0, 0).fuse(cyl(HOSE_PORT_D / 2 - 0.2, WALL + 1.6, 0, 0, 1.5))
    g = g.fuse(Part.makeCone(HOSE_PORT_D / 2 + 0.5, HOSE_PORT_D / 2 - 0.2, 1.2, V(0, 0, 1.5 + WALL + 0.1)))
    return g.cut(cyl(TUBE_OD / 2 - 0.15, 10, 0, 0, -0.1))


def make_cylinder_stand():
    base = rbox(130, 80, 4, 8)
    rad = CYL_D / 2 + 1
    seat_z = 4 + 6 + rad
    for x in (20, 96):
        saddle = Part.makeBox(14, CYL_D * 0.8, seat_z * 0.78, V(x, 40 - CYL_D * 0.4, 0))
        base = base.fuse(saddle)
    base = base.cut(cyl(rad, 140, -5, 40, seat_z, V(1, 0, 0)))
    return base, seat_z


# ------------------------------------------------------------------ bought parts (placeholders)

def vitamins(cradle_seat_z):
    v = {}
    axis_z = FLOOR + cradle_seat_z
    px, py = PUMP_POS
    v["pump_motor"] = cyl(PUMP_D / 2, PUMP_LEN * 0.6, px, py, axis_z, V(1, 0, 0))
    v["pump_head"] = Part.makeBox(PUMP_LEN * 0.4, 34, 30, V(px + PUMP_LEN * 0.6, py - 17, axis_z - 15))
    vx, vy = VALVE_POS
    v["vent_valve"] = Part.makeBox(30, 16, 16, V(vx, vy - 8, FLOOR + 3)).fuse(cyl(9, 20, vx + 15, vy, FLOOR + 19))
    plx, ply = PLATE_POS
    bx, by, bz = perfboard_origin()
    v["perfboard"] = Part.makeBox(PERF[0], PERF[1], 1.6, V(bx, by, bz - 1.6))
    # On the perfboard: ESP32 along the back (USB end towards the left wall), MOSFET boards in
    # front of it, buck converter at the right end. The sensor sits on the plate beside the board.
    v["esp32"] = Part.makeBox(51, 28, 12, V(bx, by + 22, bz))
    v["mosfet_pump"] = Part.makeBox(33, 18, 8, V(bx, by + 2, bz))
    v["mosfet_valve"] = Part.makeBox(33, 18, 8, V(bx + 35, by + 2, bz))
    v["buck_5v"] = Part.makeBox(17, 22, 6, V(bx + 53, by + 26, bz))
    sx, sy, sz = plx + 86, ply + 20, FLOOR + 2.5
    v["pressure_sensor"] = Part.makeBox(14, 19, 10, V(sx, sy, sz)).fuse(cyl(2.5, 8, sx + 7, sy, sz + 5, V(0, -1, 0)))
    gx, gy = GAUGE_POS
    v["gauge"] = cyl(20, 26, gx, gy, H - 26).fuse(cyl(21.5, 1.5, gx, gy, H + LID_T))
    v["gauge_face"] = cyl(19, 0.4, gx, gy, H + LID_T + 1.5)
    v["stop_button"] = cyl(8, 28, STOP_POS[0], STOP_POS[1], H - 28).fuse(cyl(10, 2, STOP_POS[0], STOP_POS[1], H + LID_T))
    v["stop_cap"] = cyl(7.5, 4, STOP_POS[0], STOP_POS[1], H + LID_T + 2)
    rw, rh = ROCKER_CUT
    v["rocker_switch"] = Part.makeBox(rw - 0.4, rh - 0.4, 20, V(ROCKER_POS[0] - rw / 2 + 0.2, ROCKER_POS[1] - rh / 2 + 0.2, H - 20)).fuse(
        Part.makeBox(rw + 2, rh + 2, 4, V(ROCKER_POS[0] - rw / 2 - 1, ROCKER_POS[1] - rh / 2 - 1, H + LID_T)))
    v["status_led"] = cyl(2.5, 6, LED_POS[0], LED_POS[1], H - 2)
    v["dc_jack"] = cyl(5.2, 18, 145, D - WALL - 15, 35, V(0, 1, 0)).fuse(cyl(7, 2, 145, D, 35, V(0, 1, 0)))
    v["relief_valve"] = cyl(6.2, 26, W - WALL - 24, 40, 40, V(1, 0, 0)).fuse(cyl(8, 10, W, 40, 40, V(1, 0, 0)))
    # Tubing: pump head -> tee by the valve -> hose port, plus branches to relief valve and sensor.
    tee = V(150, VALVE_POS[1], FLOOR + 22)
    hx = px + PUMP_LEN
    pts = [V(hx, py, axis_z), V(hx + 8, py, axis_z), V(hx + 8, VALVE_POS[1], FLOOR + 22), tee]
    tubes = []
    for a, b in list(zip(pts, pts[1:])) + [(tee, V(150, -2, FLOOR + 22)), (tee, V(150, 40, FLOOR + 22)),
                                      (V(150, 40, FLOOR + 22), V(W - WALL - 24, 40, 40)), (V(vx + 15, vy, FLOOR + 30), V(vx + 15, vy, FLOOR + 22)),
                                      (V(vx + 15, vy, FLOOR + 22), tee), (V(150, 40, FLOOR + 22), V(150, sy - 10, FLOOR + 22)),
                                      (V(150, sy - 10, FLOOR + 22), V(sx + 7, sy - 10, FLOOR + 22)),
                                      (V(sx + 7, sy - 10, FLOOR + 22), V(sx + 7, sy - 10, sz + 5)),
                                      (V(sx + 7, sy - 10, sz + 5), V(sx + 7, sy - 8, sz + 5))]:
        d = b.sub(a)
        if d.Length > 0.1:
            tubes.append(Part.makeCylinder(TUBE_OD / 2, d.Length, a, d))
        tubes.append(Part.makeSphere(TUBE_OD / 2, b))
    v["tubing"] = Part.makeCompound(tubes)
    return v


# ------------------------------------------------------------------ build + export

def main():
    for sub in ("step", "stl", os.path.join("blender", "parts")):
        os.makedirs(os.path.join(HERE, sub), exist_ok=True)

    base = make_base()
    lid = make_lid()
    cradle, seat_z = make_pump_cradle()
    bracket = make_valve_bracket()
    plate = make_electronics_plate()
    grommet = make_grommet()
    stand, stand_seat = make_cylinder_stand()

    # Printed parts, placed in the assembly.
    px, py = PUMP_POS
    def placed(shape, x=0, y=0, z=0, rot=None):
        s = shape.copy()
        if rot:
            s.rotate(V(0, 0, 0), rot[0], rot[1])
        s.translate(V(x, y, z))
        return s

    printed = {
        "base": (base, base),
        "lid": (lid, placed(lid, rot=(V(1, 0, 0), 180), z=0)),
        "pump_cradle_a": (placed(cradle, px + 6, py, FLOOR), cradle),
        "pump_cradle_b": (placed(cradle, px + PUMP_LEN * 0.6 - 20, py, FLOOR), None),
        # The valve rests on the bracket's base and is zip-tied to its wall.
        "valve_bracket": (placed(bracket, VALVE_POS[0] - 2, VALVE_POS[1] - 13, FLOOR), bracket),
        "electronics_plate": (placed(plate, PLATE_POS[0], PLATE_POS[1], FLOOR), plate),
        "hose_grommet": (placed(grommet, 150, -1.5, FLOOR + 22, rot=(V(1, 0, 0), -90)), grommet),
        "cylinder_stand": (placed(stand, -150, 25, 0), stand),
    }
    bought = vitamins(seat_z)

    doc = App.newDocument("VacController")
    g_printed = doc.addObject("App::DocumentObjectGroup", "Printed")
    g_bought = doc.addObject("App::DocumentObjectGroup", "Bought")
    objs = []
    report = []
    for name, (assembled, printable) in printed.items():
        o = doc.addObject("Part::Feature", name)
        o.Shape = assembled
        g_printed.addObject(o)
        objs.append(o)
        if printable is not None:
            shape = printable.copy()
            bb = shape.BoundBox
            shape.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))  # sit on the print bed
            shape.exportStep(os.path.join(HERE, "step", name.replace("_a", "") + ".step"))
            m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.3, Relative=False)
            m.write(os.path.join(HERE, "stl", name.replace("_a", "") + ".stl"))
            report.append((name.replace("_a", ""), shape.isValid(), shape.Volume / 1000.0,
                           (round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1))))
    for name, shape in bought.items():
        o = doc.addObject("Part::Feature", name)
        o.Shape = shape
        g_bought.addObject(o)
        objs.append(o)
    doc.recompute()
    doc.saveAs(os.path.join(HERE, "VacController.FCStd"))
    Import.export(objs, os.path.join(HERE, "step", "assembly.step"))

    # Blender: every part in place + manifest (colour, group, explode offset in mm).
    colours = {
        "base": (0.11, 0.12, 0.14), "lid": (0.11, 0.12, 0.14), "pump_cradle_a": (0.85, 0.35, 0.10),
        "pump_cradle_b": (0.85, 0.35, 0.10), "valve_bracket": (0.85, 0.35, 0.10), "electronics_plate": (0.85, 0.35, 0.10),
        "hose_grommet": (0.15, 0.15, 0.15), "cylinder_stand": (0.11, 0.12, 0.14),
        "pump_motor": (0.70, 0.72, 0.75), "pump_head": (0.08, 0.08, 0.08), "vent_valve": (0.75, 0.62, 0.25),
        "perfboard": (0.20, 0.45, 0.20), "esp32": (0.12, 0.15, 0.35), "buck_5v": (0.10, 0.30, 0.60),
        "mosfet_pump": (0.10, 0.10, 0.45), "mosfet_valve": (0.10, 0.10, 0.45), "pressure_sensor": (0.15, 0.15, 0.15),
        "gauge": (0.75, 0.76, 0.78), "gauge_face": (0.95, 0.95, 0.93), "stop_button": (0.12, 0.12, 0.12),
        "stop_cap": (0.80, 0.08, 0.08), "rocker_switch": (0.10, 0.10, 0.10), "status_led": (0.10, 0.90, 0.30),
        "dc_jack": (0.20, 0.20, 0.20), "relief_valve": (0.80, 0.65, 0.30), "tubing": (0.85, 0.88, 0.90),
    }
    explode = {"lid": (0, 0, 90), "gauge": (0, 0, 90), "gauge_face": (0, 0, 90), "stop_button": (0, 0, 90),
               "stop_cap": (0, 0, 90), "rocker_switch": (0, 0, 90), "status_led": (0, 0, 90),
               "pump_motor": (0, 0, 45), "pump_head": (0, 0, 45), "pump_cradle_a": (0, 0, 25), "pump_cradle_b": (0, 0, 25),
               "vent_valve": (0, 0, 45), "valve_bracket": (0, 0, 25), "perfboard": (0, 0, 50), "esp32": (0, 0, 60),
               "buck_5v": (0, 0, 60), "mosfet_pump": (0, 0, 60), "mosfet_valve": (0, 0, 60), "pressure_sensor": (0, 0, 60),
               "electronics_plate": (0, 0, 30), "tubing": (0, 0, 35), "dc_jack": (0, 40, 0), "relief_valve": (40, 0, 0),
               "hose_grommet": (0, -40, 0)}
    manifest = []
    for o in objs:
        m = MeshPart.meshFromShape(Shape=o.Shape, LinearDeflection=0.08, AngularDeflection=0.35, Relative=False)
        m.write(os.path.join(HERE, "blender", "parts", o.Name + ".stl"))
        manifest.append({"name": o.Name, "file": "parts/" + o.Name + ".stl",
                         "group": "printed" if o.Name in printed else "bought",
                         "color": colours.get(o.Name, (0.6, 0.6, 0.6)), "explode": explode.get(o.Name, (0, 0, 0))})
    with open(os.path.join(HERE, "blender", "manifest.json"), "w") as f:
        json.dump({"units": "mm", "box": [W, D, H + LID_T],
                   "gauge_center": [GAUGE_POS[0], GAUGE_POS[1], H + LID_T + 2.0], "gauge_radius": 19.0,
                   "stop_cap": "stop_cap", "led_name": "status_led", "pump_parts": ["pump_motor", "pump_head"],
                   "hose_port": [150.0, -2.0, FLOOR + 22],
                   # The bought cylinder, lying on the printed stand (placed at x = -150, y = 25).
                   "cylinder": {"start": [-160.0, 25 + 40, stand_seat], "length": 150.0, "radius": CYL_D / 2},
                   "parts": manifest}, f, indent=1)

    print("\nPrinted parts (valid, volume cm3, size mm):")
    for name, ok, vol, size in report:
        print(f"  {name:18s} valid={ok}  {vol:7.1f} cm3  {size}")
    print("saved", os.path.join(HERE, "VacController.FCStd"))


main()
