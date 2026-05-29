# Universal ESP32 Button/Signal Bridge

Compact **ESP32-S3** board for personal automation — safely interfaces with low-voltage
buttons, LEDs, buzzers, and control panels (intercoms, appliance panels, remotes,
ventilation controls).

> ⚠️ **LOW VOLTAGE ONLY — NOT designed to switch 230 V mains.** Relays use low-voltage
> contacts only.

**Status:** paper design, rev 0.1 (schematic notes + KiCad project skeleton; not yet
laid out or prototyped).

## Features

- **ESP32-S3-WROOM-1-N8** module (pre-certified, no PSRAM so GPIO35/36/37 stay free)
- USB-C power + **native USB-Serial-JTAG** programming (no CH340/CP2102 needed)
- 5 V external input + AMS1117-3.3 regulator
- **8** optically isolated inputs (≈3–24 V DC, constant-current front end, active-low)
- **8** PhotoMOS isolated dry-contact outputs (AQY212GS, ≤60 V / ≤0.5 A)
- **2** optional mechanical relay outputs (MOSFET-driven, flyback, LV contacts only)
- **4** capacitive-touch injection outputs (100 k / 470 k / 1 M selectable)
- Status LED, BOOT + RESET buttons, UART debug + spare-GPIO headers
- Screw terminals + test points; 4-layer; 0603-min passives; JLCPCB/LCSC sourcing

## Files

| File | Description |
|------|-------------|
| [DESIGN.md](DESIGN.md) | Block diagram, GPIO map, strapping-pin policy, per-block schematics, ERC/DRC notes, warnings, I/O-expander fallback |
| [BOM.csv](BOM.csv) | Bill of materials with example parts / LCSC codes (verify before ordering) |
| [block-diagram.txt](block-diagram.txt) | ASCII block diagram |
| `universal-esp32-bridge.kicad_pro` | KiCad 8 project |
| `universal-esp32-bridge.kicad_sch` | Starter schematic (design notes embedded) |

## GPIO summary

23 signals on direct ESP32-S3 GPIO (inputs 4/5/6/7/15/16/17/18, PhotoMOS
8/9/10/11/12/13/14/21, relays 35/36, cap-inject 37/38/39/40, LED 2). Strapping pins
GPIO3/45/46 left unconnected; GPIO0 used only by BOOT button. See [DESIGN.md](DESIGN.md).

## Disclaimer

Unverified paper design. Build and bring up one channel of each type before populating
all channels. Confirm all part numbers and footprints before ordering.
