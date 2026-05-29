# Universal ESP32 Button/Signal Bridge — Design Package

**Rev:** 0.1 (paper design)
**Date:** 2026-05-29
**MCU module:** ESP32-S3-WROOM-1-N8 (8 MB flash, **no** PSRAM — chosen so GPIO35/36/37 stay free)
**PCB:** 4-layer, signal / GND / PWR / signal
**Passives:** 0603 minimum (0805/1206 where power dictates). No 0201/01005.
**Sourcing target:** JLCPCB / LCSC

> ⚠️ **SAFETY / SCOPE**
> This board is for **low-voltage signal-level** automation only (≈3–24 V DC on inputs,
> ≤60 V / ≤0.5 A on isolated outputs). It is **NOT designed to switch 230 V mains** and
> must never be wired to mains. The mechanical relays use low-voltage contacts only.
> Silk legend to print: **"LOW VOLTAGE ONLY — NOT FOR MAINS (230 V) SWITCHING".**

---

## 1. Block Diagram

```
                              USB-C (power + native USB-Serial-JTAG)
                                 │ VBUS 5V        │ D+ / D-
                                 │                │ (GPIO20 / GPIO19)
                  ┌──────────────┴───┐        ┌───┴───────────────┐
   EXT 5V IN ───►│  Diode-OR (SS54)  │        │ USBLC6-2SC6 ESD    │
   (screw term)  │  reverse-prot     │        └───┬───────────────┘
                 └──────────┬────────┘            │
                            │ 5V rail (~4.6V)      │
              ┌─────────────┼──────────────┐      │
              │             │              │      │
        ┌─────┴─────┐  ┌────┴─────┐   ┌────┴──────┴──────────────────┐
        │ AMS1117-  │  │ Relay    │   │      ESP32-S3-WROOM-1-N8       │
        │ 3.3 LDO   │  │ coils 5V │   │  (3.3V, native USB, buttons)  │
        └─────┬─────┘  └────┬─────┘   └──┬───┬────┬────┬────┬────┬─────┘
              │ 3.3V rail   │            │   │    │    │    │    │
              ├─────────────┼────────────┘   │    │    │    │    │
              │             │                 │    │    │    │    │
   ┌──────────┴───┐  ┌──────┴──────┐  ┌──────┴─┐ ┌┴────┴┐ ┌─┴────┴─┐
   │ 8× ISOLATED  │  │ 8× PhotoMOS │  │ 2× RLY │ │4× CAP│ │ STATUS │
   │ INPUTS       │  │ DRY-CONTACT │  │ driver │ │ inject│ │ LED    │
   │ (opto + CRD) │  │ OUTPUTS     │  │ +flybk │ │ 100k/ │ │ GPIO2  │
   │ 3–24V DC     │  │ ≤60V/≤0.5A  │  │ MOSFET │ │ 470k/ │ └────────┘
   └──────┬───────┘  └──────┬──────┘  └───┬────┘ │ 1M    │
          │                 │             │      └──┬────┘
     screw terminals   screw terminals  screw t.  pads/term
     IN1..IN8 (+/-)    OUT1..OUT8 (A/B) RLY1/2    CAP1..4

   Test points: 3V3, 5V, GND, IN1..8 (logic side), OUT1..8, plus BOOT/EN.
```

Full-resolution block diagram source: see `block-diagram.txt`.

---

## 2. GPIO Pin Map (ESP32-S3-WROOM-1)

**Reserved / avoided:** GPIO0 (BOOT strap), GPIO3 / GPIO45 / GPIO46 (straps),
GPIO19/GPIO20 (native USB D-/D+), GPIO43/GPIO44 (UART0 console — kept free for debug).

| Function          | Signal | GPIO   | Notes                                            |
|-------------------|--------|--------|--------------------------------------------------|
| Isolated input 1  | IN1    | GPIO4  | opto pulls LOW when external signal present      |
| Isolated input 2  | IN2    | GPIO5  | (active-low, invert in firmware)                 |
| Isolated input 3  | IN3    | GPIO6  |                                                  |
| Isolated input 4  | IN4    | GPIO7  |                                                  |
| Isolated input 5  | IN5    | GPIO15 |                                                  |
| Isolated input 6  | IN6    | GPIO16 |                                                  |
| Isolated input 7  | IN7    | GPIO17 |                                                  |
| Isolated input 8  | IN8    | GPIO18 |                                                  |
| PhotoMOS out 1    | OUT1   | GPIO8  | HIGH = contact closed                            |
| PhotoMOS out 2    | OUT2   | GPIO9  |                                                  |
| PhotoMOS out 3    | OUT3   | GPIO10 |                                                  |
| PhotoMOS out 4    | OUT4   | GPIO11 |                                                  |
| PhotoMOS out 5    | OUT5   | GPIO12 |                                                  |
| PhotoMOS out 6    | OUT6   | GPIO13 |                                                  |
| PhotoMOS out 7    | OUT7   | GPIO14 |                                                  |
| PhotoMOS out 8    | OUT8   | GPIO21 |                                                  |
| Relay 1 drive     | RLY1   | GPIO35 | via MOSFET; HIGH = energized                     |
| Relay 2 drive     | RLY2   | GPIO36 |                                                  |
| Cap inject 1      | CAP1   | GPIO37 | through 100k/470k/1M jumper                       |
| Cap inject 2      | CAP2   | GPIO38 |                                                  |
| Cap inject 3      | CAP3   | GPIO39 |                                                  |
| Cap inject 4      | CAP4   | GPIO40 |                                                  |
| Status LED        | LED    | GPIO2  | active-high through 1k                           |
| Boot button       | —      | GPIO0  | strap, 10k PU + 0.1µF, button to GND             |
| Reset button      | —      | EN     | 10k PU + 1µF, button to GND                      |
| USB D-            | —      | GPIO19 | native USB-Serial-JTAG                           |
| USB D+            | —      | GPIO20 |                                                  |
| (free / spare)    | —      | GPIO1, GPIO41, GPIO42, GPIO47, GPIO48 | bring to a header for future use |

**23 signals assigned, 5 GPIOs spare.** GPIO35/36/37 are only free on **non-PSRAM**
modules (N8). If you buy an `R8` (octal PSRAM) variant, those three pins disappear —
re-map relays/cap1 to spares (GPIO47/48/41).

### 2.1 Strapping-pin handling (explicit)

ESP32-S3 has 4 strapping pins sampled at reset. This design's policy:

| Strap pin | Default latch | Used in this design? | Handling |
|-----------|---------------|----------------------|----------|
| GPIO0     | 1 = SPI boot  | **Yes — BOOT button** | 10k pull-up + 0.1µF + button to GND. Default HIGH = normal boot; pull LOW only while pressing BOOT. No other load on this net. |
| GPIO3     | float = JTAG src | **No** | Left unconnected (no-connect flag). Not routed to any channel. |
| GPIO45    | 0 = VDD_SPI 3.3V | **No** | Left unconnected. Do not load — must read its default at boot. |
| GPIO46    | 0 (ROM msg ctrl), input-only | **No** | Left unconnected. Input-only anyway, so never used as an output. |

No isolated-input, PhotoMOS, relay, or cap-inject channel is mapped onto a strapping
pin. The only strap intentionally driven is GPIO0, and only by the BOOT button — exactly
its intended ESP-IDF use. This keeps power-on boot deterministic.

> Also note GPIO19/20 (USB) and GPIO43/44 (UART0) are reserved, not channel pins.

### 2.2 I/O Expander Option (fallback — NOT used in V1)

**V1 default = direct ESP32-S3 GPIO** for every channel (28 usable pins ≥ 23 needed, so
no expander is required and none is fitted). This section documents the fallback **only**
for the case where layout/routing of 22 channel traces to the module proves too messy on
the chosen board size — per your instruction, propose the expander before ever cutting
channels.

**Proposed expander: MCP23017** (16-bit I²C GPIO expander, 0603-friendly SSOP/SOIC,
on LCSC, 5V/3.3V tolerant, two address pins → up to 8 on one bus, has INT outputs).

What moves to the expander vs. stays direct:

| Channel group        | On expander? | Why |
|----------------------|--------------|-----|
| 8 PhotoMOS outputs   | ✅ yes        | Slow on/off; I²C latency irrelevant. |
| 2 relay outputs      | ✅ yes        | Same — set-and-forget. |
| Status LED           | ✅ yes        | Trivial. |
| 8 isolated inputs    | ⚠️ optional   | OK via MCP23017 INT pin → 1 ESP32 GPIO interrupt; on-chip pull-ups + INT-on-change. Slightly more firmware. |
| **4 cap-inject**     | ❌ **stay direct** | Charge-transfer timing needs real-time GPIO toggling — an I²C expander is far too slow. Always on native ESP32 GPIO. |

**Two sizing options:**
- **1× MCP23017** → all 8 PhotoMOS + 2 relays + status LED (11 of 16 pins). Inputs + 4
  cap-inject stay on direct GPIO. Frees ~11 ESP32 pins. Cost: 1 chip, I²C (SDA/SCL =
  e.g. GPIO8/GPIO9) + 1 INT line if you later move inputs over.
- **2× MCP23017** (addresses 0x20/0x21) → bank A = 8 outputs+2 relays+LED, bank B = 8
  inputs (with INT). Only cap-inject + I²C + INTs remain direct: **~6 ESP32 GPIOs total.**
  This is also what would let a pin-limited C3 run the full board — but we are staying on
  S3, so this is purely a routing-relief option.

**Trade-offs to weigh before choosing it:**
- Adds I²C bus (2 pull-ups 4.7k), 1–2 chips, decoupling — more BOM, but *fewer* long
  channel traces fanning out to the module (often a net routing win on a dense 4-layer).
- Output update rate via I²C is ~fine (sub-ms for a few pins); inputs lose hardware
  per-pin interrupt granularity (one shared INT, read register to find which pin).
- Firmware: ESPHome has an `mcp23017`/`mcp23xxx` platform, so channels still expose
  cleanly later.

**Decision for V1: do NOT populate an expander.** Keep the MCP23017 footprint(s) + I²C
pull-ups as an **optional DNP footprint** on the board if you want a no-respin escape
hatch; otherwise route direct. Revisit only if 4-layer routing of the 22 channels can't
close at the target board size.

---

## 3. Schematic Design (per-block, as readable netlists)

Reference designators below match the KiCad skeleton sheets you'll wire up.

### 3.1 Power

```
USB-C J1:
  VBUS ──► D1 (SS54 Schottky, anode VBUS, cathode 5V_RAIL)
  CC1 ── R1 5.1k ── GND        (Rd, sink advertise)
  CC2 ── R2 5.1k ── GND
  D+/D- ── USBLC6-2SC6 (U2) ── GPIO20 / GPIO19   (ESD clamp + pass-through)
  SHIELD ── (NP) ── chassis/GND via 1M ∥ 4.7nF footprint

EXT 5V screw terminal J2 (5V, GND):
  5V_in ──► D2 (SS54, anode in, cathode 5V_RAIL)   (reverse-protect + OR with USB)

5V_RAIL:
  C1 100µF (1206/electrolytic) + C2 0.1µF  to GND   (bulk)
  ──► AMS1117-3.3 (U3) IN
       U3 OUT = 3V3_RAIL
       C3 22µF + C4 0.1µF on OUT to GND

3V3_RAIL:
  C5 22µF + C6 10µF + C7 0.1µF near module 3V3 pin
  TVS optional footprint D3 (SMAJ5.0A) across 5V_RAIL→GND
```

> Note: diode-OR drops the rail to ≈4.6 V. AMS1117 dropout at ~500 mA is ~1 V, leaving
> ~3.5 V headroom for the 3.3 V output — adequate but not generous. See Warnings §7.

### 3.2 ESP32-S3 module (U4 = ESP32-S3-WROOM-1-N8)

```
3V3 ── module 3V3, decoupled as above
EN  ── R3 10k to 3V3 ; C8 1µF to GND ; SW1 (RESET) to GND
GPIO0 ── R4 10k to 3V3 ; C9 0.1µF to GND ; SW2 (BOOT) to GND
GPIO19 ── USB D- (via U2)
GPIO20 ── USB D+ (via U2)
GPIO43/44 (U0TXD/RXD) ── 3-pin debug header J3 (TX, RX, GND)
Spare GPIOs (1,41,42,47,48) ── 5-pin expansion header J4
GND ── module GND pads + thermal pad
```

### 3.3 Isolated Input channel (×8, IN1…IN8) — repeat block

```
Screw terminal Jx (IN+, IN-):
  IN+ ──► CRD1 (constant-current diode ~2 mA, e.g. 1N5305 / CRD-2mA)
        ──► opto LED anode (U_INx, EL357N)
  opto LED cathode ──► IN-
  D_revx (1N4148WS) anti-parallel across opto LED (reverse clamp)
  TVS optional footprint (SMAJ24A) across IN+/IN-   [DNP default]

Opto output side (EL357N transistor):
  collector ──► R_pux 10k to 3V3   AND  ──► node INx_LOGIC
  emitter   ──► GND
  Optional RC filter footprint:
      INx_LOGIC ── R_fx (1k, DNP/0Ω default) ── INx_FILT ── C_fx (100nF, DNP) ── GND
  INx_FILT (or INx_LOGIC if RC unpopulated) ──► ESP32 GPIO
  Test point TP_INx on the logic node.
```

- **Idle (no external signal):** opto off → GPIO pulled HIGH by 10k.
- **Signal present:** opto on → GPIO pulled LOW. Treat as **active-low** in firmware.
- CRD gives ~constant LED current from ~3 V to 24 V, so brightness/threshold is
  consistent across the whole range and the series resistor never overheats.
- CRD inherently blocks reverse polarity (it's a diode) → polarity protection built in.

### 3.4 PhotoMOS dry-contact output (×8, OUT1…OUT8) — repeat block

```
ESP32 GPIO ──► R_dx 330Ω ──► PhotoMOS LED anode (U_OUTx, AQY212GS)
                              PhotoMOS LED cathode ──► GND
PhotoMOS load pins (pins 4 & 6) ──► screw terminal Jx (OUTx_A, OUTx_B)
  Optional series footprint F_x (0Ω / fuse / PTC) in OUTx_A leg  [0Ω default]
  Optional TVS/snubber footprint across OUTx_A/B  [DNP]
Test point TP_OUTx on OUTx_A.
```

- ~6.4 mA LED drive from 3.3 V through 330 Ω (AQY212 trigger IF ≈ 3 mA → solid margin).
- Output is a **bidirectional isolated solid-state contact** (no polarity), behaves like
  a momentary/maintained button. AQY212GS: 60 V / 550 mA / ~0.5 Ω on-resistance.
- GPIO HIGH = contact closed.

### 3.5 Mechanical relay output (×2, RLY1/RLY2) — optional, repeat block

```
ESP32 GPIO ──► R_gx 100Ω ──► gate of Q_x (AO3400A, logic-level N-MOSFET)
  R_pdx 100k gate-to-GND (hold off during boot)
  Q_x source ──► GND
  Q_x drain  ──► relay coil (-)   [K_x = HK4100F-DC5V or G5NB-1A-E-5VDC]
  relay coil (+) ──► 5V_RAIL
  D_fbx flyback (1N4007/M7 or SS14) across coil, cathode to 5V
Relay contacts (COM / NO [/ NC]) ──► screw terminal Jx
  Optional RC snubber footprint across contacts  [DNP]
Silk: "LV CONTACTS ONLY"
```

- Driven by MOSFET, never directly from the GPIO. Gate pulldown keeps relay off while
  GPIO0/straps settle at boot. Flyback diode mandatory.

### 3.6 Capacitive injection output (×4, CAP1…CAP4) — repeat block

```
ESP32 GPIO ──► three parallel 0603 resistor footprints to common node CAPx_OUT:
      R_100k  (100 kΩ)   } populate ONE, or use solder-jumper SJ_x to select
      R_470k  (470 kΩ)   }
      R_1M    (1 MΩ)     }
CAPx_OUT ──► 2-pin terminal / pad to external touch pad
  Optional series C footprint (DNP) + ESD diode footprint (DNP)
Test point TP_CAPx.
```

- Default-populate 470 kΩ; leave the other two unpopulated. Or fit all three and select
  with the solder jumper. High series R limits current and lets the GPIO inject a
  charge-transfer signal into an external capacitive pad for experimentation.

### 3.7 Status LED

```
GPIO2 ──► R_led 1k ──► LED1 (0603, green) ──► GND   (active-high)
```

---

## 4. Connectors & Test Points

| Ref      | Type                                   | Purpose                          |
|----------|----------------------------------------|----------------------------------|
| J1       | USB-C 16-pin SMD (TYPE-C-31-M-12)       | Power + native USB programming   |
| J2       | 2-pos 3.5 mm screw terminal             | External 5 V in                  |
| IN1–IN8  | 2-pos 3.5 mm screw terminal (×8)        | Isolated inputs (IN+/IN-)        |
| OUT1–OUT8| 2-pos 3.5 mm screw terminal (×8)        | PhotoMOS dry contacts (A/B)      |
| RLY1–RLY2| 3-pos 3.5 mm screw terminal (×2)        | Relay COM/NO/NC                  |
| CAP1–CAP4| 2-pos 3.5 mm screw terminal (×4)        | Cap-inject outputs               |
| J3       | 3-pin 2.54 header                       | UART0 debug (TX/RX/GND)          |
| J4       | 5-pin 2.54 header                       | Spare GPIO expansion             |
| TP_*     | 1.0 mm test pads                        | 3V3, 5V, GND, IN1-8, OUT1-8      |

> JST-XH alternative: every 3.5 mm terminal footprint can be swapped for JST-XH if you
> prefer cable connectors — keep the same pin order. Pick one in layout; don't fit both.

---

## 5. Suggested BOM (real parts)

See `BOM.csv` for the machine-readable version. Highlights:

| Block        | Part                         | Mfr / Example       | LCSC* | Notes |
|--------------|------------------------------|---------------------|-------|-------|
| MCU module   | ESP32-S3-WROOM-1-N8          | Espressif           | verify| pre-certified, no PSRAM |
| LDO 3.3V     | AMS1117-3.3                  | various             | C6186 | 1 A, beginner-proof |
| USB-C conn   | TYPE-C-31-M-12 (16P)         | various             | C165948 | power+USB |
| USB ESD      | USBLC6-2SC6                  | ST                  | C7519 | D+/D- clamp |
| OR/rev diode | SS54 (SMC)                   | various             | C22452| low-Vf 5 A Schottky |
| Input opto   | EL357N(B) (×8)               | Everlight           | C124981 | SMD, high CTR |
| Input CCR    | constant-current diode ~2 mA (×8) | e.g. 1N5305 / CRD | verify| see Warnings §7 |
| Input clamp  | 1N4148WS (×8)                | various             | C2128 | reverse clamp |
| PhotoMOS     | AQY212GS (×8)                | Panasonic           | verify| 60V/550mA/0.5Ω |
| PhotoMOS alt | CPC1017N (×8)                | IXYS/Clare          | verify| 60V/100mA cheap alt |
| Relay        | HK4100F-DC5V (×2)            | HuiKe               | C39562| LV contacts only |
| Relay MOSFET | AO3400A (×2)                 | AOS                 | C20917| logic-level N-ch |
| Flyback      | 1N4007 / M7 (×2)             | various             | C95872| across coil |
| Status LED   | 0603 green                   | various             | —     | |
| Buttons      | 6×3.5 mm SMD tact (×2)       | various             | C318884| BOOT + RESET |
| Bulk caps    | 100µF/16V, 22µF, 10µF        | various             | —     | power filtering |
| Passives     | 0603 R/C as listed           | various             | —     | 1% resistors |
| Terminals    | 3.5 mm screw, 2P/3P          | various             | —     | I/O |

\* **LCSC codes must be verified before ordering** — codes drift and packaging
varies. Treat the manufacturer part numbers as authoritative and confirm the LCSC
stock code + footprint on lcsc.com at order time.

---

## 6. ERC / DRC Notes

**ERC (schematic):**
- Every opto/PhotoMOS LED needs its series element (CRD or 330 Ω) — ERC won't catch a
  missing current limit; check manually.
- Mark `5V_RAIL`, `3V3_RAIL`, `GND` as global power nets; add a `PWR_FLAG` on the LDO
  output, the 5V rail, and GND or ERC will report "input power pin not driven".
- Set unused module pins to "unconnected" (place no-connect flags) to silence ERC.
- Active-low inputs are intentional — don't let ERC/firmware assume active-high.
- BOOT (GPIO0) and EN have pull-ups + caps; verify no other driver fights them.

**DRC (layout, 4-layer):**
- **Isolation:** keep a clearance gap (≥1.5–2 mm, ideally a routed slot) between the
  field side (screw terminals / opto+PhotoMOS LED-output pins, relay contacts) and the
  logic side. The whole point of the optos/PhotoMOS is galvanic isolation — don't pour
  the logic GND plane under the field-side terminals. Use separate "field" copper.
- Inputs at 24 V are low energy, but still give input traces ≥0.3 mm and terminal-to-
  terminal spacing per your terminal pitch.
- Relay coil + PhotoMOS traces that may carry up to 0.5 A: ≥0.4 mm (16 mil) traces.
- USB D+/D-: route as a loose differential pair, short, away from switching nodes;
  put the USBLC6 right at the connector.
- Decoupling caps within a few mm of the module 3V3 pin; bulk cap near the LDO.
- Thermal: AMS1117 needs copper pour on its tab for >300 mA continuous.
- Place the module antenna at a board edge with **keep-out** (no copper/plane under the
  antenna) per Espressif's WROOM-1 layout guide.
- Add fab fiducials + the "NOT FOR MAINS" silk legend.

---

## 7. Warnings & Uncertain Items

1. **Wide-range input current limiting (most important).** A single fixed resistor that
   gives enough opto current at 3 V *and* doesn't cook itself / over-drive the opto at
   24 V is not really possible (8:1 range). The design uses a **constant-current diode
   (CRD ~2 mA)** which solves this elegantly and adds reverse protection — but:
   - CRD knee voltage + opto Vf (~1.2 V) means the very bottom of the 3 V spec is
     marginal. Validate with your exact CRD; if 3 V must be rock-solid, pick a low-knee
     CRD or a lower-Vf opto.
   - **Alternative if you can't source a CRD on LCSC:** fit a series resistor instead
     (footprint provided), e.g. 2.2 kΩ in **1206** (handles the ~0.24 W at 24 V), and
     accept that current varies 1–10 mA across the range. The EL357N's high CTR copes.
     I left both footprints so you can choose at build time.

2. **LCSC part numbers are not all verified.** I'm confident on AMS1117 (C6186), USBLC6
   (C7519), AO3400A (C20917). The ESP32-S3 module code, CRD, AQY212GS and CPC1017N
   codes are placeholders — confirm on lcsc.com. AQY212GS in particular may have limited
   LCSC stock; CPC1017N or TLP241A are fallbacks (CPC1017N only meets 100 mA, not 550).

3. **Power rail headroom.** Diode-OR'd 5 V rail sits at ~4.6 V; AMS1117 to 3.3 V is fine
   at ESP32 average current but tight at WiFi-TX peaks (~500 mA). If you see brownout
   resets, options: (a) use a low-Vf P-FET ideal-diode instead of the Schottky OR, or
   (b) use a buck/LDO with lower dropout (e.g. an SY8089 buck for 5V→3.3V).

4. **USB current.** With plain 5.1 k CC pulldowns you only guarantee USB default current
   (~500 mA). ESP32 WiFi + both relays + several PhotoMOS can exceed that. **Power the
   relays/heavy loads from the EXT 5 V terminal** if using both relays hard, or add a
   USB-PD/BC1.2 negotiator. Documented, not auto-handled.

5. **Native USB vs UART.** I used the S3's built-in USB-Serial-JTAG (GPIO19/20) → no
   CH340/CP2102 needed. Auto-download usually works without touching buttons, but BOOT +
   RESET are included for the cases where it doesn't. If you'd rather have a classic
   USB-UART bridge with auto-reset (DTR/RTS), that's a different sub-circuit.

6. **Module variant matters.** Buy **N8 (no PSRAM)**. An `R8`/octal-PSRAM module steals
   GPIO35/36/37 — the relay + CAP1 pins. Re-map to spares if you must use R8.

7. **Isolation is only as good as the layout.** The optos/PhotoMOS provide galvanic
   isolation, but a sloppy 4-layer pour that runs the logic ground plane under the
   field-side terminals destroys it. Respect the isolation gap in §6.

8. **Test-point count is large.** 3V3+5V+GND + 8 inputs + 8 outputs = 19 pads minimum.
   They eat board area; consider a debug header block instead of individual loops if
   space is tight.

9. **This is a paper design, not validated silicon.** No SPICE sim or prototype yet.
   Build one channel of each type first (1 input, 1 PhotoMOS, 1 relay, 1 cap) on the
   first article and bring up firmware before populating all 22 channels.

---

## 8. Firmware GPIO hints (for later — ESPHome/MQTT/Matter)

- Inputs: `binary_sensor` with `inverted: true` (active-low), add `delayed_on/off` or
  the on-board RC for buzzer/blinking sources.
- PhotoMOS outputs: `switch` / `output` (active-high). For "button press" use a momentary
  `on_press` → turn on, delay 100–300 ms, turn off.
- Relays: `switch`, active-high; consider `restore_mode: ALWAYS_OFF`.
- Cap inject: `output` (or `esp32_touch` experiments) — start LOW.
- Status LED: `light`/`status_led` on GPIO2.
- Do **not** assign anything to GPIO0/3/45/46 in firmware.
