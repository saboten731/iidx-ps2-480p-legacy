# beatmania IIDX (PS2) — 480p Patch

**English** | [日本語](README.ja.md)

An unofficial patch that enables **480p video output** for the PlayStation 2 versions of *beatmania IIDX 3rd–8th style* on real PS2 hardware.

It adjusts video output and display positioning while retaining each game's original rendering resolution. **All six games have been checked on physical PS2 hardware, including gameplay.**

> **About image quality:** This is 480p *output*, not native 640×480 rendering. The existing game image is vertically scaled for progressive output; this implementation differs from the native 480p patches for 9th style and later.

## Supported games

**Latest update: [v1.21](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.21).** Download the patch for each game from the table below.

| Game | Patch | Release |
|---|---|---|
| **3rd style** | [`IIDX03_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX03_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **4th style** | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX04_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **5th style** | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX05_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **6th style** | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.21/IIDX06_480p.xdelta) | [v1.21](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.21) |
| **7th style** | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX07_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **8th style** | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX08_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |

Previous releases remain available for reference. Apply **one patch to an unmodified ISO**; do not stack patches.

## How to apply

Create an ISO from a game disc you own. Choose **either xdelta or Python**; you do not need both.

### Option 1: xdelta (recommended)

1. Download the corresponding `.xdelta` from the table above.
2. Compare the SHA-256 of your unmodified ISO with the **reference original ISO** listed in [checksums.txt](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.21/checksums.txt).
3. Apply the patch with Delta Patcher or [xdelta3](https://github.com/jmacd/xdelta/releases).
4. If needed, compare the resulting ISO's SHA-256 with the **patched ISO** entry in the same checksums file.

An xdelta applies to **one exact reference ISO**. If your input ISO hash differs, do not force the patch; consider the Python option below.

Example (replace the paths and filename as appropriate):

```sh
xdelta3 -d -s "<original ISO>" "IIDX05_480p.xdelta" "<output ISO>"
```

### Option 2: Python

Use [`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py) with **Python 3.10 or later**. No third-party packages are required.

```sh
python patch480p.py "<original ISO>"
```

The script writes a new ISO and does not modify the input. Use `--output` to choose the output path.

The Python patcher checks the supported original game data and rejects unsupported or already patched inputs. Use an unmodified ISO made from your own disc.

## Using it on a PS2

- A **480p-capable display** and compatible video connection are required.
- **Disable GSM video-mode forcing**. The patch sets 480p output itself.
- Video color output follows the PS2's **RGB/component system setting**, not automatic cable detection. **RGB output has not been tested on real hardware.**

## Hardware compatibility

### Tested setup

| ID | PS2 Model | Loader / Storage | Video Connection | Display | GSM |
|---|---|---|---|---|---|
| A | SCPH-77000 (JP) | OPL (MX4SIO / USB) | Component (D-terminal) | 480p TV (direct, no scaler) | Off |

### Hardware checks

| Setup | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| A | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Legend:** ✓ = video, audio and gameplay checked on the listed setup / — = not tested

For **5th style**, v1.2 corrects an audio playback issue that occurred when outputting 480p in v1.1. The fix adjusts two HLINE timer intervals in `IOP_MAIN.IRX`, with normal stereo playback and no accumulating audio drift observed during the hardware check.

Checks are limited to the listed hardware and sessions. Other PS2 models, displays and boot methods have not been verified. Not every song or long-duration use was exhaustively tested.

## Notes

- **No ISOs, game executables or copyrighted game assets are distributed.** Use an ISO made from your own game disc.
- The patches adjust video output and display timing. **5th style additionally adjusts an IOP audio timer** to maintain normal playback at 480p. Music assets, charts and judgment data are not intentionally modified.
- Keep your original ISO and allow space for one additional full-size ISO.
- Published patched-ISO SHA-256 values apply only to the respective reference original ISOs. A different ISO accepted by the Python patcher may produce a different output ISO hash.

## Acknowledgments

The distribution format was inspired by [blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p). This project is a separate implementation for 3rd–8th style.

## License and disclaimer

The patch software and project documentation are released under the [MIT License](LICENSE). Rights to the original games, assets and trademarks remain with their respective owners.

This is an unofficial patch and is neither endorsed nor supported by KONAMI.
