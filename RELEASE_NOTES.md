# beatmania IIDX 3rd style — 480p Patch v1.0

The first release of an unofficial 480p patch for the PlayStation 2 version of *beatmania IIDX 3rd style*.

### What's new

- Outputs the game's existing 240-line image at **480p** by doubling it vertically.
- Adjusts display positioning and video timing. **Music and chart timing remained in sync during real-hardware testing.**
- Follows the PS2 system's RGB/component video-output setting.

This does **not** convert the game to native 640×480 rendering.

### Downloads and installation

| File | Purpose |
|---|---|
| [`IIDX03_480p_v1.0.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/IIDX03_480p_v1.0.xdelta) | Patch for the exact reference ISO (recommended). |
| [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/checksums.txt) | Hashes for verifying the original and patched ISOs. |

If your ISO has a different hash, you can also use [`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy) from the repository, provided the game executable is the supported, unmodified version.

### Hardware testing and notes

Tested on a physical PS2 through the title screen, HOW TO PLAY, song selection, gameplay, key judgments, and extended operation. Test setup: OPL/MX4SIO, component (D-terminal) connection, **GSM disabled**. RGB output has not been tested on real hardware.

**Only 3rd style is supported** in this release. 4th–8th style are not supported yet.

See the [README](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/README.md) for instructions and requirements. **No game files or ISOs are included.** This is an unofficial patch and is not endorsed or supported by KONAMI.
