#pragma once
// All the numbers you might want to change live here.

// ---------------- Pins (ESP32 DevKit, WROOM-32) ----------------
#define PIN_PUMP       25   // MOSFET gate -> vacuum pump (PWM)
#define PIN_VALVE      26   // MOSFET gate -> NORMALLY-OPEN vent valve. HIGH = valve closed (sealed)
#define PIN_SENSOR     34   // pressure sensor via divider. Must be an ADC1 pin (32-39): ADC2 stops working with WiFi on
#define PIN_STOP_BTN   27   // momentary button to GND. Press = STOP. Hold 3 s = clear a fault
#define PIN_LED        2    // on-board LED. On = running, blinking = fault

// ---------------- Pressure sensor ----------------
// The 5 V sensor output goes through a divider (10k on top, 15k to GND) so the ESP32 sees <= 3.3 V.
#define DIVIDER_RATIO     (15.0f / (10.0f + 15.0f))
// Sensor output (volts, BEFORE the divider) at atmosphere and at SENSOR_FULL_KPA of vacuum.
// Defaults: XGZP6847A, -100..0 kPa version (0.5 V at -100 kPa, 4.5 V at 0 kPa).
// For an NXP MPXV6115V use 4.6 / 0.2 / 115.
#define SENSOR_V_AT_ATM   4.5f
#define SENSOR_V_AT_FULL  0.5f
#define SENSOR_FULL_KPA   100.0f
// At boot (valve open) the sensor must read within this many volts of SENSOR_V_AT_ATM, or the
// controller refuses to run. Kept tight so a stuck vacuum at power-up can't be zeroed away.
#define ZERO_TOLERANCE_V  0.20f

// ---------------- Vacuum limits (kPa of vacuum, 0 = atmosphere) ----------------
// 1 kPa = 0.30 inHg. These are conservative engineering defaults, not medical advice.
// Set the MECHANICAL relief valve at or below HARD_MAX_KPA: it is the real backstop.
#define HARD_MAX_KPA          35.0f  // firmware ceiling. Exceeding it = emergency vent + fault
#define DEFAULT_USER_MAX_KPA  15.0f  // your own max, adjustable in the app up to HARD_MAX_KPA
#define DEFAULT_LEVEL_KPA      6.0f  // starting intensity
#define OVERSHOOT_TRIP_KPA     3.0f  // running and more than this above your max = fault
#define RELEASE_OK_KPA         3.0f  // "released" means below this
#define RELEASE_TIMEOUT_MS   2500    // after STOP, vacuum must be released within this or fault
#define OVER_TARGET_KPA        2.5f  // stuck this far above target ...
#define OVER_TARGET_MS       3000    // ... for this long = vent valve not working = fault
#define SENSOR_PLAUSIBLE_POS_KPA 15.0f // readings this far ABOVE atmosphere mean a wiring fault

// ---------------- Session ----------------
#define DEFAULT_SESSION_MIN  15
#define MAX_SESSION_MIN      30
#define SOFT_START_MS     20000      // intensity ramps up over the first 20 s ...
#define SOFT_START_MIN     0.30f     // ... starting from 30 %
// Stop if no phone/browser has talked to the controller for this long (0 = never).
// Keep the control page open; the page checks in several times a second.
#define CLIENT_TIMEOUT_MS 20000

// ---------------- Pump control ----------------
#define CONTROL_PERIOD_MS   10
#define PUMP_PWM_HZ      20000
#define PUMP_MIN_DUTY      110       // lowest PWM (of 255) at which your pump still turns
#define PUMP_MAX_DUTY      255
#define PUMP_KP           25.0f      // extra duty per kPa below target
#define PUMP_DEADBAND_KPA  0.4f
#define BLEED_HYST_KPA     1.0f      // above target by this much -> short vent pulse
#define BLEED_PULSE_MS      50
#define BLEED_INTERVAL_MS  150

// ---------------- WiFi ----------------
// The controller makes its own WiFi network; join it and open http://192.168.4.1
// CHANGE THE PASSWORD (8+ characters). The app shows a warning while it is the default.
#define WIFI_AP_SSID  "VacController"
#define WIFI_AP_PASS  "change-me-123"

#define WDT_TIMEOUT_MS 3000          // firmware hang -> reboot -> outputs off -> valve vents
