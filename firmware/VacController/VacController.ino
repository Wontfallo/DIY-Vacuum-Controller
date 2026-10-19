// VacController: ESP32 controller for a DIY pulsing vacuum device.
//
// Safety is layered so no single failure leaves vacuum applied:
//   Hardware: adjustable mechanical relief valve; NORMALLY-OPEN vent valve (vents whenever it is
//             unpowered: power loss, reset, crash); power switch on the 12 V rail; STOP button.
//   Firmware: hard vacuum ceiling, overshoot trip, vent-valve self-check, sensor plausibility,
//             tight boot zero check, soft start, session timer, lost-phone stop, watchdog reboot.
//
// The control loop runs in its own task every 10 ms. The web page only changes settings or
// requests start/stop; every output change happens under one mutex.

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_task_wdt.h>
#include "config.h"
#include "web_ui.h"

// Arduino-ESP32 core 3.x renamed the PWM and watchdog APIs; both versions are supported.
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
#define VAC_CORE_V3 1
#endif

enum class State : uint8_t { Idle, Running, Fault };
enum class Mode : uint8_t { Stroke, Wave, Flutter, Build, Random, Count };
static const char *const MODE_NAMES[] = {"stroke", "wave", "flutter", "build", "random"};
static const char *const STATE_NAMES[] = {"idle", "running", "fault"};

struct Settings {
  float userMax;
  float level;
  uint8_t mode;
  uint8_t speed;      // 1..10
  uint8_t sessionMin;
};

static Settings cfg;
static Preferences prefs;
static WebServer server(80);
static SemaphoreHandle_t mtx;

static State state = State::Idle;
static char faultMsg[112] = "";
static char infoMsg[112] = "";

// Sensor (vacuum is positive kPa below atmosphere)
static const float KPA_PER_VOLT = SENSOR_FULL_KPA / (SENSOR_V_AT_ATM - SENSOR_V_AT_FULL);
static float vZero = SENSOR_V_AT_ATM;
static float sensorV = SENSOR_V_AT_ATM;
static float vac = 0;

// Outputs
static uint8_t pumpDuty = 0;
static bool valveClosed = false;

// Run state
static uint32_t runStart = 0;
static volatile uint32_t lastClientMs = 0;
static uint32_t stopRequestedMs = 0;
static float targetKpa = 0;
static bool ventPhase = false;
static uint32_t cycleStart = 0, cyclePeriod = 2000;
static float cycleDepth = 1;
static uint16_t cycleCount = 0;
static uint32_t ventStartMs = 0;
static float ventStartVac = 0;
static uint8_t releaseFails = 0;
static uint32_t overTargetSince = 0;
static uint32_t lastBleedMs = 0, bleedUntil = 0;
static bool wdtReady = false;  // resetting the watchdog before it's set up only spams the log

// ---------------------------------------------------------------- outputs

static void pwmInit() {
#ifdef VAC_CORE_V3
  ledcAttach(PIN_PUMP, PUMP_PWM_HZ, 8);
#else
  ledcSetup(0, PUMP_PWM_HZ, 8);
  ledcAttachPin(PIN_PUMP, 0);
#endif
}

static void setPump(uint8_t duty) {
  pumpDuty = duty;
#ifdef VAC_CORE_V3
  ledcWrite(PIN_PUMP, duty);
#else
  ledcWrite(0, duty);
#endif
}

static void setValve(bool closed) {
  valveClosed = closed;
  digitalWrite(PIN_VALVE, closed ? HIGH : LOW);
}

// Pump off, vent valve unpowered (open).
static void allSafe() {
  setPump(0);
  setValve(false);
}

// ---------------------------------------------------------------- sensor

static float readSensorVolts() {
  uint32_t mv = 0;
  for (int i = 0; i < 8; i++) mv += analogReadMilliVolts(PIN_SENSOR);
  return (mv / 8.0f) / 1000.0f / DIVIDER_RATIO;
}

static float volts2kpa(float v) { return (vZero - v) * KPA_PER_VOLT; }

// Vents, waits, then takes the at-rest reading as zero. Refuses readings far from the
// sensor's nominal atmosphere voltage, so a stuck vacuum or a wiring fault can't be zeroed away.
static bool zeroSensor(char *msg, size_t n) {
  allSafe();
  uint32_t t0 = millis();
  while (millis() - t0 < 1500) {
    if (wdtReady) esp_task_wdt_reset();
    delay(10);
  }
  float sum = 0;
  for (int i = 0; i < 64; i++) {
    sum += readSensorVolts();
    delay(2);
  }
  float v = sum / 64;
  sensorV = v;
  if (fabsf(v - SENSOR_V_AT_ATM) > ZERO_TOLERANCE_V) {
    snprintf(msg, n, "Sensor reads %.2f V at rest, expected about %.2f V. Check wiring and sensor type in config.h",
             v, SENSOR_V_AT_ATM);
    return false;
  }
  vZero = v;
  vac = 0;
  snprintf(msg, n, "Sensor zeroed at %.3f V", v);
  return true;
}

// ---------------------------------------------------------------- settings

static void loadSettings() {
  prefs.begin("vac", true);
  cfg.userMax = constrain(prefs.getFloat("umax", DEFAULT_USER_MAX_KPA), 1.0f, HARD_MAX_KPA);
  cfg.level = constrain(prefs.getFloat("level", DEFAULT_LEVEL_KPA), 0.0f, cfg.userMax);
  cfg.mode = prefs.getUChar("mode", 0);
  if (cfg.mode >= (uint8_t)Mode::Count) cfg.mode = 0;
  cfg.speed = constrain(prefs.getUChar("speed", 4), 1, 10);
  cfg.sessionMin = constrain(prefs.getUChar("sess", DEFAULT_SESSION_MIN), 1, MAX_SESSION_MIN);
  prefs.end();
}

static void saveSettings() {
  prefs.begin("vac", false);
  prefs.putFloat("umax", cfg.userMax);
  prefs.putFloat("level", cfg.level);
  prefs.putUChar("mode", cfg.mode);
  prefs.putUChar("speed", cfg.speed);
  prefs.putUChar("sess", cfg.sessionMin);
  prefs.end();
}

// ---------------------------------------------------------------- state changes

static void fault(const char *why) {
  allSafe();
  if (state != State::Fault) {
    state = State::Fault;
    strlcpy(faultMsg, why, sizeof faultMsg);
    infoMsg[0] = 0;
    Serial.printf("FAULT: %s\n", why);
  }
}

static uint32_t periodForSpeed(uint8_t speed) {
  return 4000 - (uint32_t)(speed - 1) * 3300 / 9;  // speed 1 = 4.0 s per stroke, 10 = 0.7 s
}

static void newCycle() {
  uint32_t base = periodForSpeed(cfg.speed);
  switch ((Mode)cfg.mode) {
    case Mode::Flutter:
      cyclePeriod = max<uint32_t>(base / 3, 300);
      cycleDepth = 0.7f;
      break;
    case Mode::Build:  // ten strokes getting deeper, then start again
      cyclePeriod = base;
      cycleDepth = 0.3f + 0.7f * ((cycleCount % 10) / 9.0f);
      break;
    case Mode::Random:
      cyclePeriod = base * (70 + esp_random() % 61) / 100;
      cycleDepth = 0.4f + (esp_random() % 61) / 100.0f;
      break;
    case Mode::Wave:
      cyclePeriod = base * 5 / 2;
      cycleDepth = 1;
      break;
    default:
      cyclePeriod = base;
      cycleDepth = 1;
  }
}

static bool startRun(char *err, size_t n) {
  if (state == State::Fault) { strlcpy(err, "Clear the fault first", n); return false; }
  if (state == State::Running) return true;
  if (vac > RELEASE_OK_KPA) { strlcpy(err, "Vacuum is not released yet", n); return false; }
  uint32_t now = millis();
  state = State::Running;
  runStart = cycleStart = lastClientMs = now;
  cycleCount = 0;
  releaseFails = 0;
  overTargetSince = 0;
  ventStartMs = 0;
  ventPhase = false;
  stopRequestedMs = 0;
  infoMsg[0] = 0;
  newCycle();
  return true;
}

static void stopRun(const char *why) {
  allSafe();
  if (state == State::Running) {
    state = State::Idle;
    stopRequestedMs = millis();
  }
  strlcpy(infoMsg, why ? why : "", sizeof infoMsg);
}

static bool clearFault(char *err, size_t n) {
  if (state != State::Fault) return true;
  if (vac > RELEASE_OK_KPA) { strlcpy(err, "Vacuum still present. Release it before clearing", n); return false; }
  if (vac < -SENSOR_PLAUSIBLE_POS_KPA) { strlcpy(err, "Sensor reading is implausible. Check wiring", n); return false; }
  state = State::Idle;
  faultMsg[0] = 0;
  stopRequestedMs = 0;
  return true;
}

// ---------------------------------------------------------------- pattern + control

// Target as a fraction (0..1) of the intensity, and whether this moment is a vent phase.
static float patternTarget(uint32_t now, bool &vent) {
  uint32_t t = now - cycleStart;
  if (t >= cyclePeriod) {
    cycleStart = now;
    cycleCount++;
    newCycle();
    t = 0;
  }
  float ph = (float)t / cyclePeriod;
  if ((Mode)cfg.mode == Mode::Wave) {  // never fully vents; rises and falls smoothly
    vent = false;
    return 0.35f + 0.65f * (0.5f - 0.5f * cosf(2 * PI * ph));
  }
  float duty = ((Mode)cfg.mode == Mode::Flutter) ? 0.5f : 0.55f;
  vent = ph >= duty;
  return vent ? 0 : cycleDepth;
}

static void controlTick(uint32_t now) {
  float v = readSensorVolts();
  sensorV += 0.35f * (v - sensorV);
  vac = volts2kpa(sensorV);

  // Checks that apply in every state.
  if (vac < -SENSOR_PLAUSIBLE_POS_KPA || vac > SENSOR_FULL_KPA * 1.1f)
    fault("Pressure sensor reading out of range. Check sensor wiring");
  if (vac > HARD_MAX_KPA) fault("Hard vacuum limit exceeded. Vented");
  if (state == State::Running && vac > min(cfg.userMax, HARD_MAX_KPA) + OVERSHOOT_TRIP_KPA)
    fault("Vacuum went above your max. Vented");

  if (state != State::Running) {
    allSafe();
    if (state == State::Idle && stopRequestedMs) {
      if (vac <= RELEASE_OK_KPA) stopRequestedMs = 0;
      else if (now - stopRequestedMs > RELEASE_TIMEOUT_MS) {
        stopRequestedMs = 0;
        fault("Vacuum did not release after stop. Use the manual release valve");
      }
    }
    return;
  }

  if (now - runStart > cfg.sessionMin * 60000UL) { stopRun("Session time reached"); return; }
  if (CLIENT_TIMEOUT_MS && now - lastClientMs > CLIENT_TIMEOUT_MS) {
    stopRun("Lost contact with the control page");
    return;
  }

  bool vent;
  float frac = patternTarget(now, vent);
  float soft = min(1.0f, SOFT_START_MIN + (1 - SOFT_START_MIN) * (now - runStart) / (float)SOFT_START_MS);
  float level = min(min(cfg.level, cfg.userMax), HARD_MAX_KPA);
  targetKpa = frac * level * soft;

  // Vent-valve self-check: each vent phase must drop the vacuum clearly. Three misses in a row
  // means the valve (or its wiring) isn't venting.
  if (vent && !ventPhase) {
    ventStartMs = now;
    ventStartVac = vac;
  }
  if (!vent && ventPhase && ventStartMs) {
    if (now - ventStartMs >= 250 && ventStartVac > RELEASE_OK_KPA) {
      bool released = vac <= max(RELEASE_OK_KPA, ventStartVac * 0.6f);
      releaseFails = released ? 0 : releaseFails + 1;
      if (releaseFails >= 3) { fault("Vacuum is not releasing. Vent valve may be stuck"); return; }
    }
  }
  ventPhase = vent;

  // Same idea for patterns that bleed instead of venting fully (Wave).
  if (vac > targetKpa + OVER_TARGET_KPA) {
    if (!overTargetSince) overTargetSince = now;
    else if (now - overTargetSince > OVER_TARGET_MS) { fault("Vacuum stuck above target. Vent valve may be stuck"); return; }
  } else {
    overTargetSince = 0;
  }

  if (vent || now < bleedUntil) {
    setPump(0);
    setValve(false);
    return;
  }
  if (vac > targetKpa + BLEED_HYST_KPA && now - lastBleedMs > BLEED_INTERVAL_MS) {
    lastBleedMs = now;
    bleedUntil = now + BLEED_PULSE_MS;
    setPump(0);
    setValve(false);
    return;
  }
  setValve(true);
  float err = targetKpa - vac;
  if (err > PUMP_DEADBAND_KPA) setPump((uint8_t)constrain(PUMP_MIN_DUTY + err * PUMP_KP, (float)PUMP_MIN_DUTY, (float)PUMP_MAX_DUTY));
  else setPump(0);
}

// Press = stop. Hold 3 s while faulted = clear the fault (only if the vacuum is released).
static void buttonTick(uint32_t now) {
  static uint8_t lowCount = 0;
  static bool pressed = false, handled = false;
  static uint32_t downAt = 0;
  bool low = digitalRead(PIN_STOP_BTN) == LOW;
  lowCount = low ? min<uint8_t>(lowCount + 1, 10) : 0;
  if (!pressed && lowCount >= 3) {  // 30 ms debounce
    pressed = true;
    handled = false;
    downAt = now;
    if (state == State::Running) stopRun("Stopped with the button");
  }
  if (pressed && !low) pressed = false;
  if (pressed && !handled && state == State::Fault && now - downAt > 3000) {
    handled = true;
    char err[112];
    if (!clearFault(err, sizeof err)) Serial.printf("Clear refused: %s\n", err);
  }
}

static void ledTick(uint32_t now) {
  bool on = state == State::Running || (state == State::Fault && (now / 250) % 2);
  digitalWrite(PIN_LED, on ? HIGH : LOW);
}

static void controlTask(void *) {
  esp_task_wdt_add(NULL);
  TickType_t last = xTaskGetTickCount();
  uint32_t lastLog = 0;
  for (;;) {
    vTaskDelayUntil(&last, pdMS_TO_TICKS(CONTROL_PERIOD_MS));
    esp_task_wdt_reset();
    xSemaphoreTake(mtx, portMAX_DELAY);
    uint32_t now = millis();
    controlTick(now);
    buttonTick(now);
    ledTick(now);
    if (state == State::Running && now - lastLog > 500) {
      lastLog = now;
      Serial.printf("vac %.1f target %.1f pump %u valve %s\n", vac, targetKpa, pumpDuty, valveClosed ? "closed" : "open");
    }
    xSemaphoreGive(mtx);
  }
}

// ---------------------------------------------------------------- web

static void sendStatus() {
  char buf[760];
  xSemaphoreTake(mtx, portMAX_DELAY);
  uint32_t elapsed = state == State::Running ? (millis() - runStart) / 1000 : 0;
  snprintf(buf, sizeof buf,
           "{\"state\":\"%s\",\"fault\":\"%s\",\"msg\":\"%s\",\"vac\":%.2f,\"target\":%.2f,"
           "\"level\":%.1f,\"userMax\":%.1f,\"hardMax\":%.1f,\"mode\":\"%s\",\"speed\":%u,"
           "\"sessionMin\":%u,\"maxSessionMin\":%u,\"elapsed\":%lu,\"pump\":%u,\"valveClosed\":%s,"
           "\"sensorV\":%.3f,\"zeroV\":%.3f,\"clientTimeout\":%lu,\"defaultPass\":%s}",
           STATE_NAMES[(int)state], faultMsg, infoMsg, vac, state == State::Running ? targetKpa : 0.0f,
           cfg.level, cfg.userMax, HARD_MAX_KPA, MODE_NAMES[cfg.mode], cfg.speed, cfg.sessionMin,
           MAX_SESSION_MIN, (unsigned long)elapsed, (unsigned)(pumpDuty * 100 / 255),
           valveClosed ? "true" : "false", sensorV, vZero, (unsigned long)CLIENT_TIMEOUT_MS,
           strcmp(WIFI_AP_PASS, "change-me-123") == 0 ? "true" : "false");
  xSemaphoreGive(mtx);
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", buf);
}

static void sendError(const char *err) {
  String body = String("{\"error\":\"") + err + "\"}";
  server.send(409, "application/json", body);
}

static void handleStatus() {
  lastClientMs = millis();
  sendStatus();
}

static void handleCmd() {
  lastClientMs = millis();
  char err[112] = "";
  bool ok = true;
  String action = server.arg("action");

  xSemaphoreTake(mtx, portMAX_DELAY);
  if (action == "stop") stopRun("Stopped");  // first, before anything else

  bool changed = false;
  if (server.hasArg("userMax")) { cfg.userMax = constrain(server.arg("userMax").toFloat(), 1.0f, HARD_MAX_KPA); changed = true; }
  if (server.hasArg("level")) { cfg.level = server.arg("level").toFloat(); changed = true; }
  cfg.level = constrain(cfg.level, 0.0f, cfg.userMax);
  if (server.hasArg("mode")) {
    String m = server.arg("mode");
    for (uint8_t i = 0; i < (uint8_t)Mode::Count; i++)
      if (m == MODE_NAMES[i] && i != cfg.mode) {
        cfg.mode = i;
        cycleStart = millis();
        cycleCount = 0;
        newCycle();
        changed = true;
      }
  }
  if (server.hasArg("speed")) { cfg.speed = constrain(server.arg("speed").toInt(), 1, 10); changed = true; }
  if (server.hasArg("session")) { cfg.sessionMin = constrain(server.arg("session").toInt(), 1, MAX_SESSION_MIN); changed = true; }

  if (action == "start") ok = startRun(err, sizeof err);
  else if (action == "clear") ok = clearFault(err, sizeof err);
  else if (action == "zero") {
    if (state == State::Running) { ok = false; strlcpy(err, "Stop before re-zeroing", sizeof err); }
    else {
      ok = zeroSensor(err, sizeof err);
      strlcpy(infoMsg, err, sizeof infoMsg);
    }
  }
  xSemaphoreGive(mtx);

  if (changed) saveSettings();
  if (!ok) sendError(err);
  else sendStatus();
}

// ---------------------------------------------------------------- setup / loop

void setup() {
  // Outputs off before anything else (the gates also have 10k pull-downs on the board).
  pinMode(PIN_PUMP, OUTPUT);
  digitalWrite(PIN_PUMP, LOW);
  pinMode(PIN_VALVE, OUTPUT);
  digitalWrite(PIN_VALVE, LOW);
  pwmInit();
  allSafe();
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_STOP_BTN, INPUT_PULLUP);
  analogSetPinAttenuation(PIN_SENSOR, ADC_11db);

  Serial.begin(115200);
  Serial.println("\nVacController starting");
  mtx = xSemaphoreCreateMutex();
  loadSettings();

  char msg[112];
  if (!zeroSensor(msg, sizeof msg)) fault(msg);
  Serial.println(msg);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASS);
  Serial.printf("WiFi \"%s\" up. Open http://%s\n", WIFI_AP_SSID, WiFi.softAPIP().toString().c_str());

  server.on("/", HTTP_GET, [] { server.send_P(200, "text/html", INDEX_HTML); });
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/cmd", HTTP_POST, handleCmd);
  server.onNotFound([] { server.send(404, "text/plain", "Not found"); });
  server.begin();

#ifdef VAC_CORE_V3
  esp_task_wdt_config_t wdt = {};
  wdt.timeout_ms = WDT_TIMEOUT_MS;
  wdt.idle_core_mask = 0;
  wdt.trigger_panic = true;
  esp_task_wdt_reconfigure(&wdt);
#else
  esp_task_wdt_init(WDT_TIMEOUT_MS / 1000, true);
#endif
  esp_task_wdt_add(NULL);  // this (loop) task
  wdtReady = true;

  // Control loop on core 1 above the web server's priority.
  xTaskCreatePinnedToCore(controlTask, "control", 4096, nullptr, 3, nullptr, 1);
}

void loop() {
  esp_task_wdt_reset();
  server.handleClient();
  delay(2);
}
