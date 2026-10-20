# beatmania IIDX 3rd style — 480p Patch

**English** | [日本語](README.ja.md)

An unofficial patch that enables **480p video output** for the PlayStation 2 version of *beatmania IIDX 3rd style* on real PS2 hardware.

It doubles the game's existing 240-line image vertically for 480p output, with adjustments to display positioning and video timing. **Song selection and gameplay have been tested on a physical PS2.**

> **About image quality:** This is 480p output, not a conversion to native 640×480 rendering. It uses a different approach from the native 480p patches for 9th style and later.

## Supported games

- **beatmania IIDX 3rd style (PS2)** — Supported and hardware-tested in v1.0.
- **4th–8th style** — Not supported yet. Additional games are planned as they are completed and verified.

## How to apply

Create an ISO from a disc you own. There are two ways to apply the patch: **xdelta** or **Python**. You only need one of them.

### Option 1: xdelta (recommended)

1. Download [`IIDX03_480p_v1.0.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/IIDX03_480p_v1.0.xdelta) from [Releases](https://github.com/saboten731/iidx-ps2-480p-legacy/releases).
2. Check that your original ISO's SHA-256 matches the **reference ISO** listed in the release's [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/checksums.txt).
3. Apply the patch with an xdelta-compatible tool such as Delta Patcher.

The xdelta file works **only with that exact reference ISO**. If your ISO has a different hash, use the Python patcher below instead.

Command-line example (xdelta3):

```sh
xdelta3 -d -s "beatmania IIDX 3rd style.iso" "IIDX03_480p_v1.0.xdelta" "beatmania IIDX 3rd style_480p.iso"
```

The ISO filename is just an example; substitute the name of your own file.

### Option 2: Python (for ISOs with different hashes)

Download `patch480p.py` from the [repository](https://github.com/saboten731/iidx-ps2-480p-legacy). Requires Python 3.8 or later; no third-party packages are needed.

```sh
python patch480p.py "beatmania IIDX 3rd style.iso"
```

The script leaves your original ISO untouched and creates a new file with `_480p_v1.0` added to its name. Use `--output` to choose a different output path.

The Python patcher can handle an ISO with a different overall hash **if its game executable is an exact match for the supported, unmodified version**. Other revisions and modified executables are rejected. This does not guarantee compatibility with every rebuilt ISO.

## Using it on a PS2

- You need a **480p-capable display** and a connection that supports 480p. Hardware testing used a component (D-terminal) connection.
- **Disable GSM video-mode forcing.** The patch configures 480p output from within the game.
- Video color output follows the PS2 system's **RGB/component setting**; the patch does not detect the connected cable. RGB output has not been tested on real hardware.

Testing was performed on a physical PS2 using OPL and MX4SIO, connected directly to a component-input TV with GSM disabled. The title screen, HOW TO PLAY, song selection, gameplay, key judgments, and extended operation were checked. Other displays and boot methods may behave differently.

## Notes

- **No ISO or game data are distributed.** You must supply an ISO made from your own game disc.
- The patch changes video output; it does not modify music data, charts, or judgment logic.
- Allow enough free disk space for another full-size ISO. Keep your original ISO and refer to `checksums.txt` to verify the reference ISO and patched output. The output hash may differ when patching a supported ISO with different contents outside the game executable.

## Acknowledgments

The distribution format was inspired by [blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p). This patch is a separate implementation for 3rd style.

## License and disclaimer

The patch software and project documentation are released under the [MIT License](LICENSE). All rights to the original game, its assets, and its trademarks remain with their respective owners.

This is an unofficial patch and is neither endorsed nor supported by KONAMI.
