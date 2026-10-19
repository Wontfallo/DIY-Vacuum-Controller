"""Collision check for the assembled model. Run after build_cad.py:
    "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" cad/check_fit.py
Lists any two parts that overlap by more than 0.5 mm3, except pairs that are meant to touch.
"""
import itertools
import os

import FreeCAD as App

HERE = os.path.dirname(os.path.abspath(__file__))
doc = App.openDocument(os.path.join(HERE, "VacController.FCStd"))
objs = [o for o in doc.Objects if o.TypeId == "Part::Feature" and o.Name != "cylinder_stand"]

# Parts that pass through or press against each other by design.
expected = {frozenset(p) for p in [
    ("lid", "gauge"), ("lid", "stop_button"), ("lid", "rocker_switch"), ("lid", "status_led"),
    ("gauge", "gauge_face"), ("stop_button", "stop_cap"), ("base", "dc_jack"), ("base", "relief_valve"),
    ("base", "hose_grommet"), ("pump_motor", "pump_head"), ("tubing", "pump_head"), ("tubing", "vent_valve"),
    ("tubing", "relief_valve"), ("tubing", "pressure_sensor"), ("tubing", "hose_grommet"), ("tubing", "base"),
]}

hits = []
for a, b in itertools.combinations(objs, 2):
    if frozenset((a.Name, b.Name)) in expected or not a.Shape.BoundBox.intersect(b.Shape.BoundBox):
        continue
    try:
        vol = a.Shape.common(b.Shape).Volume
    except Exception:
        vol = -1.0  # boolean failed: report it so it gets looked at
    if vol > 0.5 or vol < 0:
        hits.append((round(vol, 1), a.Name, b.Name))

for vol, a, b in sorted(hits, reverse=True):
    print(f"CLASH {a} <-> {b}: {vol} mm3")
print(f"checked {len(objs)} parts: {len(hits)} unexpected overlaps")
