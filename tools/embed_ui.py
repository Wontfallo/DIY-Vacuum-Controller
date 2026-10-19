"""Copy ui/index.html into firmware/VacController/web_ui.h so the ESP32 can serve it.

Run after editing the page:  python tools/embed_ui.py
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
html = (root / "ui" / "index.html").read_text(encoding="utf-8")
delim = "VACUI"
if f"){delim}\"" in html:
    raise SystemExit("index.html contains the raw-string delimiter; pick another one")

out = root / "firmware" / "VacController" / "web_ui.h"
out.write_text(
    "#pragma once\n"
    "// Generated from ui/index.html by tools/embed_ui.py. Edit the HTML, then re-run the script.\n"
    "#include <pgmspace.h>\n"
    f'const char INDEX_HTML[] PROGMEM = R"{delim}({html}){delim}";\n',
    encoding="utf-8",
)
print(f"wrote {out} ({len(html.encode('utf-8'))} bytes of HTML)")
