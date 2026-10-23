# beatmania IIDX (PS2) — 480p Patch

**English** | [日本語](README.ja.md)

An unofficial patch that enables **480p video output** for the PlayStation 2 versions of *beatmania IIDX 3rd–8th style* on real PS2 hardware.

It adjusts the game's video output and display positioning while retaining the original rendering resolution. **All six supported games have been tested on a physical PS2, including gameplay.**

> **About image quality:** This is 480p *output*, not native 640×480 rendering. The game's existing image is vertically scaled for the progressive signal. This implementation differs from the native 480p patches for 9th style and later.

## Supported games

| Game | Patch | Release |
|---|---|---|
| **3rd style** | [`IIDX03_480p_v1.0.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/IIDX03_480p_v1.0.xdelta) | [v1.0](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.0) |
| **4th style** | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX04_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **5th style** | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX05_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **6th style** | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX06_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **7th style** | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX07_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **8th style** | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX08_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |

**3rd style** remains available in the original **v1.0** release. **v1.1** adds patches for **4th–8th style**; you do not need to download both releases for a single game.

## How to apply

Create an ISO from a game disc you own. Choose **either xdelta or Python**—you do not need both.

### Option 1: xdelta (recommended)

1. Download the `.xdelta` file for your game from the table above.
2. Check the SHA-256 of your original ISO against the **reference original ISO** for that game: [v1.0 checksums (3rd)](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/checksums.txt) or [v1.1 checksums (4th–8th)](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/checksums.txt).
3. Apply the patch with an xdelta-compatible tool (such as Delta Patcher or [xdelta3](https://github.com/jmacd/xdelta/releases)).
4. If desired, compare the SHA-256 of the resulting ISO with the corresponding **patched ISO** hash in the same checksums file.

Each xdelta is built for **one exact reference ISO**. If the original ISO hash differs, do not force the xdelta patch. See the Python option below.

Example with xdelta3 (replace the placeholders with your own paths and choose the patch for your game):

```sh
xdelta3 -d -s "<original ISO>" "IIDX04_480p.xdelta" "<output ISO>"
```

### Option 2: Python (for a different ISO hash)

Download [`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py) from this repository. Use **Python 3.10 or later**; no third-party Python packages are required.

```sh
python patch480p.py "<original ISO>"
```

The script creates a separate patched ISO without modifying the original. Use `--output` to specify an output path.

The Python patcher can also work with an ISO whose overall hash differs from the reference **if its game executable is the exact supported, unmodified version**. Different executables and previously patched images are rejected. Compatibility with every rebuilt ISO is not guaranteed.

## Using it on a PS2

- A **480p-capable display** and a video connection that supports 480p are required.
- **Disable GSM video-mode forcing.** The patch sets the video mode within the game.
- Video color output follows the PS2 system's **RGB/component setting**; the connected cable is not auto-detected. **RGB output has not been tested on real hardware.**

## Hardware compatibility

### Tested setups

| ID | PS2 Model | Loader / Storage | Video Connection | Display | GSM |
|---|---|---|---|---|---|
| A | SCPH-77000 (JP) | OPL / MX4SIO | Component (D-terminal) | 480p TV (direct, no scaler) | Off |

### Compatibility matrix

| Setup | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| A | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Legend:** ✓ = Tested OK / ✗ = Confirmed issue / — = Not tested

A passing result means that video output and gameplay were confirmed on the listed hardware setup. Compatibility with other PS2 models, video connections, displays, or boot methods has not been verified. Testing does not cover every song or extended operation.

## Notes

- **No ISOs, game files, or copyrighted game assets are distributed.** Provide an ISO made from your own game disc.
- This patch changes video output, not music data, charts, or judgment logic.
- Keep your original ISO and allow enough disk space for a second full-size ISO.
- The published patched-ISO SHA-256 values apply to the **reference original ISOs**. An ISO accepted by the Python patcher with different non-executable contents may produce a different output hash.

## Acknowledgments

The distribution format was inspired by [blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p). This project is a separate implementation for 3rd–8th style.

## License and disclaimer

The patch software and project documentation are released under the [MIT License](LICENSE). All rights to the original games, their assets, and their trademarks remain with their respective owners.

This is an unofficial patch and is neither endorsed nor supported by KONAMI.
