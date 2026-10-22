# beatmania IIDX (PS2) — 480p Patch v1.1

**English** | [日本語](RELEASE_NOTES.ja.md)

This release expands the unofficial PS2 480p patch from **3rd style to 3rd–8th style**. New patches are available for **4th, 5th, 6th, 7th, and 8th style**, each tested on a physical PS2.

### What's new

- Added 480p output support for **4th–8th style**.
- Adjusted video output and display positioning for each game. Display and gameplay were confirmed on real hardware.
- Preserved the games' original rendering resolution. This is **480p output, not native 640×480 rendering**.
- **3rd style is unchanged** and remains available in [v1.0](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.0).

### Downloads

| Game | Patch |
|---|---|
| 4th style | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX04_480p.xdelta) |
| 5th style | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX05_480p.xdelta) |
| 6th style | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX06_480p.xdelta) |
| 7th style | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX07_480p.xdelta) |
| 8th style | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX08_480p.xdelta) |

Use [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/checksums.txt) to verify the **reference original ISO**, the expected **patched ISO**, and the downloaded patch file. Each xdelta works **only with its exact reference original ISO**. No ISO or game data are included.

For a supported unmodified game executable in a differently hashed ISO, you can use [`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py) instead. Refer to the [README](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/README.md) for instructions.

### Hardware testing and notes

The five newly supported games were checked on a physical PS2, including display and gameplay, using OPL/MX4SIO, a component (D-terminal) connection, and **GSM disabled**. Other displays and boot methods may differ. **RGB output has not been hardware-tested**, and all songs and extended operation were not exhaustively tested across every title.

This is an unofficial patch, neither endorsed nor supported by KONAMI. All game copyrights and trademarks remain with their respective owners.
