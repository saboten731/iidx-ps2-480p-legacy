# beatmania IIDX (PS2) — 480p Patch v1.2

**English** | [日本語](RELEASE_NOTES.ja.md)

v1.2 updates the 480p patches for **all six PS2 games, 3rd–8th style**, with the new shared BIOS-native 480p output method. **All six were tested on a physical PS2**, including video, audio and gameplay.

### What's changed

- Updated **3rd–8th style** to the shared BIOS-native 480p implementation and revised the display adjustments for each game.
- **Fixed 5th style audio playback in 480p mode.** The previous v1.1 patch could play different music in the left and right channels and produce incorrect menu sound effects. v1.2 adjusts two HLINE timer intervals in its `IOP_MAIN.IRX`. Stereo audio and gameplay were checked on real hardware without accumulating audio drift.
- Retained the games' original rendering resolution: **480p output, not native 640×480 rendering**.

**Important for 5th style:** The v1.1 xdelta has a confirmed audio issue on the tested real PS2 setup. Use the new **v1.2 patch applied to an unmodified ISO**; do not stack patches.

### Downloads

| Game | Patch |
|---|---|
| 3rd style | [`IIDX03_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX03_480p.xdelta) |
| 4th style | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX04_480p.xdelta) |
| 5th style | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX05_480p.xdelta) |
| 6th style | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX06_480p.xdelta) |
| 7th style | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX07_480p.xdelta) |
| 8th style | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX08_480p.xdelta) |

Use [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/checksums.txt) to verify the reference original ISO, the resulting patched ISO and the downloaded xdelta. An xdelta requires the **exact matching original ISO**. The [`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py) alternative accepts only supported original executables; **5th style additionally requires the supported original `IOP_MAIN.IRX`**. See the [README](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/README.md) for instructions. No ISO or game data is distributed.

### Hardware testing and limitations

Tested on a Japanese SCPH-77000 via OPL (MX4SIO / USB), a component (D-terminal) connection and **GSM disabled**. Video, audio and gameplay were checked for all six games. **RGB output has not been hardware-tested**, and other console models, setups and every song/extended play have not been exhaustively checked.

The earlier [v1.0](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.0) and [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) releases remain archived; **v1.2 is the recommended version**.

This is an unofficial patch, neither endorsed nor supported by KONAMI. All game rights and trademarks remain with their owners.
