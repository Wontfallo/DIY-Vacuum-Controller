# DIY Vacuum Controller (Build B)

An ESP32 replacement for the control box in the AliExpress "fully automatic milking machine" kits. It has a real pressure sensor, closed-loop control, five patterns, a phone control page, and more safety layers than the commercial units.

**Start with `showcase.html`.** It's one interactive page with everything below: the 3D model, printable parts, shopping list, wiring, plumbing, the control app simulator and a build checklist. Double-click to open it in your browser. Rebuild it with `python tools/build_showcase.py` after changing anything.

```
diy-vacuum-controller/
  showcase.html        the whole project on one interactive page
  firmware/            ESP32 firmware (Arduino IDE or PlatformIO), compiles clean
    VacController/       VacController.ino, config.h (all settings), web_ui.h (generated)
    platformio.ini
  ui/index.html        phone control page source (opens as a simulator in any browser)
  tools/embed_ui.py    copies ui/index.html into the firmware after you edit it
  cad/                 parametric FreeCAD model + printable files
    build_cad.py         the model. Edit PARAMETERS, then re-run
    check_fit.py         collision check of the assembled model
    render_previews.py   PNG previews (cad/previews/)
    VacController.FCStd  full assembly for FreeCAD
    stl/                 printable parts, already in print orientation
    step/                printed parts + assembly.step for any CAD program
    blender/demo.py      Blender demo: turntable, exploded view, running pulse cycle
```

---

## 1. Safety, read first

No single failure should leave vacuum applied. The safety is layered:

| Layer | What it does |
|---|---|
| **Normally-open vent valve** | Vents whenever it is unpowered: power cut, crash, reset or a broken wire |
| **Mechanical relief valve** | Physically cannot exceed its setting, whatever the electronics do. **Set it first (step 6).** |
| **Firmware hard limit** | `HARD_MAX_KPA` (35 kPa ≈ 10 inHg) → instant vent and latched fault |
| **Overshoot trip** | Running more than 3 kPa above *your* max → vent and fault |
| **Vent self-test** | Every vent phase must actually drop the vacuum; 3 misses → fault |
| **Release check** | After STOP, the vacuum must be gone within 2.5 s or a fault tells you to use the manual release |
| **Sensor checks** | Boot-time zero must be near the expected voltage; out-of-range readings → fault |
| **Soft start, session timer** | Ramps up over 20 s; stops after 15 min by default (30 min max) |
| **Lost-phone stop** | Stops if the control page hasn't checked in for 20 s |
| **Watchdog** | A firmware hang reboots the ESP32 → outputs off → the valve vents |
| **STOP button + power switch** | Physical, always work |

Use rules: start at the lowest intensity, keep sessions short, and never use it while drowsy or leave it running unattended. Stop if you feel pain or numbness or see discoloration. If you have a bleeding disorder, take blood thinners or have nerve damage (e.g. diabetic neuropathy), check with a doctor first. The limits in `config.h` are conservative engineering defaults, not medical advice. Only the cylinder and sleeves touch the body: buy proper silicone/TPE replacement parts and **never 3D-print anything that touches skin** (FDM prints are porous and can't be cleaned properly).

---

## 2. Parts (about $70–110 total)

AliExpress search terms in quotes. Measure your actual parts and adjust `cad/build_cad.py` if they differ.

| Part | Search / spec | Qty | ~$ |
|---|---|---|---|
| ESP32 dev board | "ESP32 DevKit V1 WROOM-32" (30- or 38-pin) | 1 | 5 |
| Vacuum pump | "12V diaphragm vacuum pump" (≈28 mm motor, −60 kPa or so is plenty) | 1 | 8–15 |
| Vent valve, **normally open** | "12V solenoid valve normally open air mini" | 1 | 4–8 |
| Pressure sensor | "XGZP6847A -100kPa~0 5V" (0.5–4.5 V output) | 1 | 5–8 |
| MOSFET switch boards | "AOD4184 MOSFET module" or "D4184 module" (switch fully at 3.3 V; **not** the IRF520 boards) | 2 | 3 |
| Flyback diodes | 1N5819 or SS34 | 2 | 1 |
| 12 V → 5 V buck | "Mini560 5V" or "MP1584 buck" | 1 | 2 |
| Power adapter | 12 V 3 A, **UL/CE listed**, 5.5×2.1 plug (buy locally) | 1 | 12 |
| Panel DC jack | "DC-022 5.5x2.1 panel mount" (11 mm hole) | 1 | 1 |
| Inline fuse | 3 A blade or 5×20 holder | 1 | 2 |
| Rocker switch | "KCD1 rocker switch" | 1 | 1 |
| STOP button | "16mm momentary push button" (red) | 1 | 2 |
| Status LED | 5 mm green + 330 Ω | 1 | – |
| Vacuum gauge | "40mm vacuum gauge -1 0 bar" (−100 to 0 kPa) | 1 | 5 |
| Adjustable relief valve | "adjustable vacuum relief valve" / "vacuum breaker valve" | 1 | 5–10 |
| Manual release valve | "mini ball valve 1/8" on the tee, opens to air | 1 | 3 |
| Fluid trap + filter | small sealed jar with 2 barbs + "inline hydrophobic filter" | 1 | 4 |
| Tubing + tees | 4×6 mm silicone tube, 6 mm barb tees | 1 m / 3 | 4 |
| Resistors | 10 k ×3, 15 k ×1, 330 Ω ×1 | | – |
| Perfboard | 70×50 mm | 1 | 1 |
| Hardware | 4× M3 heat-set inserts + M3×10 screws, M3×8 self-tappers, zip ties, rubber feet, 1.5 mm foam | | 5 |
| Cylinder + sleeves | buy as **replacement parts** from the kit sellers | | 15–40 |

---

## 3. Wiring

```
 12V adapter ─► DC jack ─► fuse 3A ─► rocker switch ─►─┬─────────────► +12V bus
                                                      │
 GND ─────────────────────────────────────────────────┴──────────────► GND bus (common with ESP32)

 +12V bus ─► buck IN        buck OUT 5V ─► ESP32 VIN (5V pin)  and  sensor VCC

 PUMP:   +12V ─► pump(+)   pump(−) ─► MOSFET-1 OUT−      MOSFET-1 SIG ◄─ GPIO25
         diode across pump: cathode (stripe) to +12V
 VALVE:  +12V ─► valve(+)  valve(−) ─► MOSFET-2 OUT−     MOSFET-2 SIG ◄─ GPIO26
         diode across coil: cathode to +12V
         10k from GPIO25 to GND and from GPIO26 to GND (keeps both OFF during boot)

 SENSOR: OUT ─► 10k ─►─┬─► GPIO34          (divider keeps the ESP32 below 3.3 V)
                       └─► 15k ─► GND
 STOP:   GPIO27 ─► button ─► GND           (internal pull-up)
 LED:    GPIO2 ─► 330Ω ─► LED ─► GND
```

| ESP32 pin | Goes to | Notes |
|---|---|---|
| GPIO25 | pump MOSFET signal | PWM 20 kHz |
| GPIO26 | vent valve MOSFET signal | HIGH = valve closed (sealing) |
| GPIO34 | sensor via 10k/15k divider | must be an ADC1 pin (32–39) |
| GPIO27 | STOP button to GND | press = stop, hold 3 s = clear fault |
| GPIO2 | lid LED (and on-board LED) | on = running, blinking = fault |
| VIN / GND | buck 5 V / common ground | |

---

## 4. Plumbing

```
 cylinder ─► fluid trap ─► filter ─► hose port ─► TEE ─┬─► pump
                                                       ├─► vent valve (normally open) ─► exhaust hole
                                                       ├─► relief valve (side wall)
                                                       ├─► manual release ball valve
                                                       ├─► gauge
                                                       └─► pressure sensor
```
The fluid trap and filter sit **outside** the box, before the hose port, so nothing liquid can reach the pump.

---

## 5. Printing

| File | Qty | Material | Orientation / notes |
|---|---|---|---|
| `stl/base.stl` | 1 | PETG (or PLA) | as exported, opening up. No supports. 180×130 mm fits a 220 mm bed |
| `stl/lid.stl` | 1 | PETG | as exported, top face down (labels print on the bed side). No supports |
| `stl/pump_cradle.stl` | **2** | PETG | flat side down. Line the saddle with 1.5 mm foam |
| `stl/valve_bracket.stl` | 1 | PETG/PLA | as exported |
| `stl/electronics_plate.stl` | 1 | PETG/PLA | as exported. The perfboard screws onto its standoffs (M2) |
| `stl/hose_grommet.stl` | 1 | **TPU** | flange down |
| `stl/cylinder_stand.stl` | 1 | PETG/PLA | as exported. Holds the cylinder when not in use |

Suggested settings: 0.2 mm layers, 3 walls, 20 % infill. Press the M3 heat-set inserts into the four corner bosses with a soldering iron. The floor has a 10 mm grid of holes, so the cradles, bracket and plate screw down anywhere with M3 self-tappers.

**Changing the design:** open `cad/build_cad.py` and edit the PARAMETERS block (pump diameter, cut-out sizes, layout). Then, in PowerShell from the `diy-vacuum-controller` folder, run the next two commands. The `&` is required in PowerShell before a quoted program path.
```powershell
& "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" cad/build_cad.py
```
```powershell
& "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" cad/check_fit.py
```
The second command must print `0 unexpected overlaps`. For fresh preview images, run `cad/render_previews.py` the same way. The bought parts in the model are simple placeholder shapes for checking fit. To view and edit the model by hand, open `cad/VacController.FCStd` in FreeCAD.

---

## 6. Firmware and first power-up

1. **Edit `firmware/VacController/config.h`:** set `WIFI_AP_PASS` (8+ characters). Change the sensor numbers only if you use a different sensor.
2. **Upload.** Either PlatformIO: run `& "$HOME/.platformio/penv/Scripts/pio.exe" run -t upload` in `firmware/`. Or Arduino IDE with the "esp32" boards package (core 2.x or 3.x): open `VacController.ino`, pick "ESP32 Dev Module", then Upload.
3. **Serial monitor (115200).** It should say `Sensor zeroed at 4.5xx V` and print the WiFi name.
4. **Set the relief valve before closing the box.** Power the pump straight from 12 V, block the hose port, and turn the relief valve until the gauge stops rising at **≤ 30 kPa (≈ 9 inHg)**. That stays below the firmware's 35 kPa hard limit.
5. **Check the sensor against the gauge.** Join the "VacController" WiFi and open `http://192.168.4.1`. With the port still blocked, start at a low intensity and compare the app's reading with the gauge at a few levels. If they disagree by more than ~1 kPa, fix the sensor numbers in `config.h`.
6. **Test every stop path before first use:**
   - **STOP button:** pressing it releases the vacuum.
   - **App STOP:** works the same.
   - **Power switch:** cutting power releases the vacuum (this proves the valve is normally open).
   - **Lost phone:** close the page and it stops within 20 s.
   - **Manual release valve:** opening it releases the vacuum.

**Editing the control page:** change `ui/index.html` (open it in a browser and it runs as a simulator), then run `python tools/embed_ui.py` and re-upload.

---

## 7. Using it

- **Patterns:** Stroke (classic on/off), Wave (smooth rise and fall, never fully vents), Flutter (fast short strokes), Build (10 strokes getting deeper, then repeat), Random.
- **Controls:** Intensity (kPa / inHg), Speed 1–10, session length.
- **Limits & diagnostics:** "My max" caps the intensity and asks for confirmation when you raise it. There's also sensor re-zero and live pump/valve state.
- **Faults:** a fault stops everything and shows why. Clear it in the app or by holding STOP for 3 s, which only works once the vacuum has been released.

---

## 8. Blender demo

`cad/blender/demo.py` builds a 14-second animation:
1. Turntable of the closed box
2. Exploded view and reassembly
3. A running stroke cycle: the gauge needle pulses, the pump vibrates and the LED glows
4. STOP pressed: everything vents

In PowerShell from the `diy-vacuum-controller` folder:
```powershell
& "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --python cad/blender/demo.py
```
```powershell
& "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --python cad/blender/demo.py -- --render
```
The first saves `cad/blender/vaccontroller_demo.blend`, which you can open in Blender and scrub through. The second also renders `cad/blender/render/vaccontroller_demo.mp4` (about 10 minutes). Use `-- --still` instead for a single exploded-view PNG. You can also open the script in Blender's Scripting tab and press Run Script. Tested on Blender 5.2.2.
