#pragma once
// Generated from ui/index.html by tools/embed_ui.py. Edit the HTML, then re-run the script.
#include <pgmspace.h>
const char INDEX_HTML[] PROGMEM = R"VACUI(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Vac Controller</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--text:#16181d;--muted:#6b7280;--line:#e3e5ea;--accent:#2563eb;--ok:#16a34a;--warn:#d97706;--bad:#dc2626;--track:#e5e7eb}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#eef0f4;--muted:#9aa1ad;--line:#2a2f38;--accent:#60a5fa;--ok:#22c55e;--warn:#f59e0b;--bad:#ef4444;--track:#2a2f38}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:12px 16px 120px}
h1{font-size:17px;margin:0;display:flex;align-items:center;gap:8px}
.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.dot{width:9px;height:9px;border-radius:50%;background:var(--bad);display:inline-block}
.dot.on{background:var(--ok)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.banner{border-radius:12px;padding:12px 14px;margin-bottom:12px;display:none}
.banner.show{display:block}
.banner.fault{background:color-mix(in srgb,var(--bad) 14%,var(--card));border:1px solid var(--bad)}
.banner.warn{background:color-mix(in srgb,var(--warn) 14%,var(--card));border:1px solid var(--warn)}
.banner b{display:block;margin-bottom:4px}
.gauge{position:relative;max-width:320px;margin:0 auto}
.gauge svg{width:100%;display:block}
.readout{position:absolute;left:0;right:0;bottom:6px;text-align:center}
.big{font-size:40px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
.unit{color:var(--muted);font-size:13px}
.chips{display:flex;justify-content:center;gap:8px;margin-top:10px;flex-wrap:wrap}
.chip{font-size:12px;padding:3px 10px;border-radius:999px;background:var(--track);color:var(--muted)}
.chip.run{background:color-mix(in srgb,var(--ok) 20%,var(--card));color:var(--ok)}
.chip.fault{background:color-mix(in srgb,var(--bad) 20%,var(--card));color:var(--bad)}
label{display:flex;justify-content:space-between;font-weight:600;font-size:13px;margin:14px 0 6px}
label:first-child{margin-top:0}
label span{font-weight:400;color:var(--muted);font-variant-numeric:tabular-nums}
input[type=range]{width:100%;accent-color:var(--accent);height:28px}
.seg{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;background:var(--track);border-radius:10px;padding:3px}
.seg button{border:0;background:none;color:var(--text);padding:9px 2px;border-radius:8px;font:inherit;font-size:13px;cursor:pointer}
.seg button.on{background:var(--card);box-shadow:0 1px 3px rgba(0,0,0,.15);font-weight:600}
select{width:100%;padding:9px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);font:inherit}
.btn{border:0;border-radius:12px;padding:12px;font:inherit;font-weight:700;cursor:pointer;width:100%}
.btn.sec{background:var(--track);color:var(--text);font-weight:600}
.bar{position:fixed;left:0;right:0;bottom:0;padding:12px 16px calc(12px + env(safe-area-inset-bottom));background:var(--bg);border-top:1px solid var(--line);display:grid;grid-template-columns:1fr 1fr;gap:10px}
.start{background:var(--ok);color:#fff;font-size:18px;padding:16px}
.stop{background:var(--bad);color:#fff;font-size:18px;padding:16px}
.start:disabled{opacity:.4}
details summary{cursor:pointer;font-weight:600}
.diag{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;font-size:13px;color:var(--muted);margin-top:10px;font-variant-numeric:tabular-nums}
.note{font-size:12px;color:var(--muted);margin-top:8px}
.toast{position:fixed;left:16px;right:16px;bottom:96px;background:var(--text);color:var(--bg);border-radius:10px;padding:10px 14px;font-size:14px;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.show{opacity:.95}
</style>
</head>
<body>
<div class="top"><h1>Vac Controller</h1><span class="unit"><span class="dot" id="dot"></span> <span id="conn">connecting</span></span></div>

<div class="banner fault" id="faultBox"><b>Stopped for safety</b><div id="faultMsg"></div>
  <button class="btn sec" id="clearBtn" style="margin-top:10px">Clear fault</button></div>
<div class="banner warn" id="passBox"><b>Default WiFi password</b>Anyone nearby could join and control this device. Change WIFI_AP_PASS in config.h and re-upload.</div>

<div class="card">
  <div class="gauge">
    <svg viewBox="0 0 200 116" aria-hidden="true">
      <path d="M20 106 A80 80 0 0 1 180 106" fill="none" stroke="var(--track)" stroke-width="14" stroke-linecap="round"/>
      <path id="arcMax" d="M20 106 A80 80 0 0 1 180 106" fill="none" stroke="color-mix(in srgb,var(--warn) 35%,transparent)" stroke-width="14" stroke-linecap="round" pathLength="100" stroke-dasharray="0 100"/>
      <path id="arcVal" d="M20 106 A80 80 0 0 1 180 106" fill="none" stroke="var(--accent)" stroke-width="14" stroke-linecap="round" pathLength="100" stroke-dasharray="0 100"/>
      <line id="tgt" x1="100" y1="18" x2="100" y2="34" stroke="var(--text)" stroke-width="3" stroke-linecap="round" transform="rotate(-90 100 106)" opacity="0"/>
    </svg>
    <div class="readout"><div class="big" id="vac">0.0</div><div class="unit"><span id="vacIn">0.0</span> inHg · kPa of vacuum</div></div>
  </div>
  <div class="chips"><span class="chip" id="stateChip">idle</span><span class="chip" id="timeChip">15:00</span><span class="chip" id="tgtChip">target 0.0</span></div>
  <div class="note" id="msg" style="text-align:center"></div>
</div>

<div class="card">
  <label>Pattern</label>
  <div class="seg" id="modes">
    <button data-m="stroke">Stroke</button><button data-m="wave">Wave</button><button data-m="flutter">Flutter</button><button data-m="build">Build</button><button data-m="random">Random</button>
  </div>
  <label for="level">Intensity <span id="levelV"></span></label>
  <input type="range" id="level" min="0" max="15" step="0.5">
  <label for="speed">Speed <span id="speedV"></span></label>
  <input type="range" id="speed" min="1" max="10" step="1">
  <label for="session">Session length</label>
  <select id="session"></select>
</div>

<div class="card">
  <details>
    <summary>Limits &amp; diagnostics</summary>
    <label for="userMax">My max <span id="userMaxV"></span></label>
    <input type="range" id="userMax" min="1" max="35" step="0.5">
    <div class="note">Intensity can never go above this. The firmware hard limit is <span id="hardV"></span>, and the mechanical relief valve should be set at or below it.</div>
    <button class="btn sec" id="zeroBtn" style="margin-top:12px">Re-zero sensor (cylinder off / vented)</button>
    <div class="diag">
      <div>Sensor</div><div id="dSensor">–</div>
      <div>Zero</div><div id="dZero">–</div>
      <div>Pump</div><div id="dPump">–</div>
      <div>Vent valve</div><div id="dValve">–</div>
    </div>
    <div class="note" id="timeoutNote"></div>
  </details>
</div>

<div class="bar"><button class="btn start" id="startBtn">Start</button><button class="btn stop" id="stopBtn">STOP</button></div>
<div class="toast" id="toast"></div>

<script>
const $ = (id) => document.getElementById(id);
const inHg = (k) => (k * 0.2953).toFixed(1);
let st = null, dragging = null, failCount = 0;

// ---- transport (real device, or a simulator when opened as a local file / with ?mock) ----
const MOCK = !/^https?:$/.test(location.protocol) || new URLSearchParams(location.search).has('mock');
const api = MOCK ? makeMock() : {
  status: () => fetch('/api/status', { cache: 'no-store' }).then((r) => r.json()),
  cmd: (params) => fetch('/api/cmd?' + new URLSearchParams(params), { method: 'POST' })
    .then(async (r) => { const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Request failed'); return j; }),
};

function toast(t) {
  const el = $('toast'); el.textContent = t; el.classList.add('show');
  clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove('show'), 3000);
}
async function send(params) {
  try { render(await api.cmd(params)); } catch (e) { toast(e.message); }
}

function render(s) {
  st = s;
  const pct = (v) => Math.max(0, Math.min(100, (v / s.hardMax) * 100));
  $('vac').textContent = s.vac.toFixed(1);
  $('vacIn').textContent = inHg(s.vac);
  $('arcVal').setAttribute('stroke-dasharray', pct(s.vac) + ' 100');
  $('arcVal').setAttribute('stroke', s.vac > s.userMax ? 'var(--bad)' : 'var(--accent)');
  $('arcMax').setAttribute('stroke-dasharray', `0 ${pct(s.userMax)} ${100 - pct(s.userMax)} 0`);
  const t = $('tgt');
  t.setAttribute('transform', `rotate(${-90 + pct(s.target) * 1.8} 100 106)`);
  t.setAttribute('opacity', s.state === 'running' ? 1 : 0);

  const chip = $('stateChip');
  chip.textContent = s.state; chip.className = 'chip ' + (s.state === 'running' ? 'run' : s.state === 'fault' ? 'fault' : '');
  const left = s.state === 'running' ? s.sessionMin * 60 - s.elapsed : s.sessionMin * 60;
  $('timeChip').textContent = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}${s.state === 'running' ? ' left' : ''}`;
  $('tgtChip').textContent = 'target ' + s.target.toFixed(1);
  $('msg').textContent = s.msg || '';

  $('faultBox').classList.toggle('show', s.state === 'fault');
  $('faultMsg').textContent = s.fault;
  $('passBox').classList.toggle('show', !!s.defaultPass);
  $('startBtn').disabled = s.state !== 'idle';
  $('startBtn').textContent = s.state === 'running' ? 'Running' : 'Start';
  $('zeroBtn').disabled = s.state === 'running';

  document.querySelectorAll('#modes button').forEach((b) => b.classList.toggle('on', b.dataset.m === s.mode));
  if (dragging !== 'level') { $('level').max = s.userMax; $('level').value = s.level; }
  if (dragging !== 'speed') $('speed').value = s.speed;
  if (dragging !== 'userMax') { $('userMax').max = s.hardMax; $('userMax').value = s.userMax; }
  showLabels();

  const sel = $('session');
  if (sel.options.length !== s.maxSessionMin / 5) {
    sel.innerHTML = '';
    for (let m = 5; m <= s.maxSessionMin; m += 5) sel.add(new Option(m + ' min', m));
  }
  if (document.activeElement !== sel) sel.value = s.sessionMin;

  $('hardV').textContent = `${s.hardMax} kPa (${inHg(s.hardMax)} inHg)`;
  $('dSensor').textContent = s.sensorV.toFixed(3) + ' V';
  $('dZero').textContent = s.zeroV.toFixed(3) + ' V';
  $('dPump').textContent = s.pump + ' %';
  $('dValve').textContent = s.valveClosed ? 'closed (sealing)' : 'open (vented)';
  $('timeoutNote').textContent = s.clientTimeout
    ? `Keep this page open and the screen on: the device stops if it loses contact for ${s.clientTimeout / 1000} s.` : '';
}

function showLabels() {
  const lv = +$('level').value, um = +$('userMax').value;
  $('levelV').textContent = `${lv.toFixed(1)} kPa · ${inHg(lv)} inHg · ${Math.round((lv / Math.max(um, 1)) * 100)}% of max`;
  $('speedV').textContent = $('speed').value + ' / 10';
  $('userMaxV').textContent = `${um.toFixed(1)} kPa · ${inHg(um)} inHg`;
}

for (const id of ['level', 'speed', 'userMax']) {
  const el = $(id);
  el.addEventListener('input', () => { dragging = id; showLabels(); });
  el.addEventListener('change', () => {
    dragging = null;
    if (id === 'userMax' && st && +el.value > st.userMax &&
        !confirm(`Raise your max to ${(+el.value).toFixed(1)} kPa? Increase limits gradually.`)) { el.value = st.userMax; showLabels(); return; }
    send({ [id]: el.value });
  });
}
$('session').addEventListener('change', (e) => send({ session: e.target.value }));
$('modes').addEventListener('click', (e) => { const m = e.target.dataset.m; if (m) send({ mode: m }); });
$('startBtn').onclick = () => send({ action: 'start' });
$('stopBtn').onclick = () => send({ action: 'stop' });
$('clearBtn').onclick = () => send({ action: 'clear' });
$('zeroBtn').onclick = () => send({ action: 'zero' });

async function poll() {
  try {
    render(await api.status());
    failCount = 0;
    $('dot').classList.add('on'); $('conn').textContent = MOCK ? 'simulator' : 'connected';
  } catch (e) {
    if (++failCount > 2) { $('dot').classList.remove('on'); $('conn').textContent = 'no connection'; }
  }
  setTimeout(poll, 300);
}
poll();

// ---- simulator: same API, simple physics, so the page can be tried without hardware ----
function makeMock() {
  const s = { state: 'idle', fault: '', msg: 'Simulator: no hardware connected', vac: 0, target: 0, level: 6, userMax: 15, hardMax: 35,
    mode: 'stroke', speed: 4, sessionMin: 15, maxSessionMin: 30, elapsed: 0, pump: 0, valveClosed: false,
    sensorV: 4.5, zeroV: 4.5, clientTimeout: 20000, defaultPass: true };
  let t0 = 0, cyc = 0, last = performance.now();
  setInterval(() => {
    const now = performance.now(), dt = (now - last) / 1000; last = now;
    if (s.state === 'running') {
      s.elapsed = Math.floor((now - t0) / 1000);
      const period = (4000 - (s.speed - 1) * 3300 / 9) / 1000 * (s.mode === 'wave' ? 2.5 : s.mode === 'flutter' ? 0.34 : 1);
      cyc = (cyc + dt / period) % 1;
      const soft = Math.min(1, 0.3 + 0.7 * (now - t0) / 20000);
      let frac = cyc < (s.mode === 'flutter' ? 0.5 : 0.55) ? 1 : 0;
      if (s.mode === 'wave') frac = 0.35 + 0.65 * (0.5 - 0.5 * Math.cos(2 * Math.PI * cyc));
      s.target = frac * Math.min(s.level, s.userMax) * soft;
    } else s.target = 0;
    const err = s.target - s.vac;
    s.valveClosed = s.state === 'running' && s.target > 0 && err > -1;
    s.pump = s.valveClosed && err > 0.4 ? Math.round(Math.min(100, 43 + err * 10)) : 0;
    s.vac += s.pump ? s.pump / 100 * 25 * dt : s.valveClosed ? 0 : -s.vac * Math.min(1, dt * 12);
    s.vac = Math.max(0, s.vac);
    s.sensorV = 4.5 - s.vac / 25;
  }, 30);
  const clone = () => Promise.resolve(JSON.parse(JSON.stringify(s)));
  return {
    status: clone,
    cmd: (p) => {
      if (p.action === 'stop') { s.state = s.state === 'running' ? 'idle' : s.state; s.msg = 'Stopped'; }
      if (p.userMax) s.userMax = Math.min(s.hardMax, Math.max(1, +p.userMax));
      if (p.level) s.level = +p.level;
      s.level = Math.min(s.level, s.userMax);
      if (p.mode) s.mode = p.mode;
      if (p.speed) s.speed = +p.speed;
      if (p.session) s.sessionMin = +p.session;
      if (p.action === 'start') {
        if (s.state === 'fault') return Promise.reject(new Error('Clear the fault first'));
        s.state = 'running'; s.msg = ''; t0 = performance.now(); cyc = 0;
      }
      if (p.action === 'clear') { s.state = 'idle'; s.fault = ''; }
      if (p.action === 'zero') s.msg = 'Sensor zeroed at 4.500 V';
      return clone();
    },
  };
}
</script>
</body>
</html>
)VACUI";
