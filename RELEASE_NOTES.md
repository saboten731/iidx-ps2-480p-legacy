# IIDX 3rd Style 480p Patch v1.0

Version 1.0 is the hardware-tested 480p patch for the PlayStation 2 release of *beatmania IIDX 3rd Style*, product code `SLPM_650.06`. It vertically doubles the existing 240-line image through the GS display circuit; it does not convert the game to native 640×480 rendering.

## Included patch

- `patch480p.py`: Python 3 patcher that validates the BOOT2 ELF and writes a separate ISO.
- `IIDX03_SLPM-65006_480p_v1.0.xdelta`: xdelta3 patch for the verified reference ISO. Download this asset from the [GitHub Releases page](https://github.com/saboten731/iidx-ps2-480p-legacy/releases), attached to v1.0.
- `checksums.txt`: SHA-256 values for the reference ISO, patched ISO, xdelta patch, and Python patcher output.

No ISO, ELF, BIOS, IRX, or game assets are included. The xdelta patch must only be used with the exact reference ISO identified by the SHA-256 in `checksums.txt`.

## Patch details

- Display: `DISPLAY=0x001DF4FF0882B138` (240 rendered lines doubled to 480 output lines).
- Video synchronization: `SYNCV=0x00C7900001E00006` (`VDP=484`).
- Runtime BIOS/OSD color selection and the game's PMODE restoration path are preserved.
- No audio pitch, chart-timer, or judgement compensation is added.

## Compatibility and verification

- v1.0 supports 3rd Style `SLPM_650.06` only. Styles 4th–8th are planned for separate analysis and validation; they are not included or supported by this release.
- The Python patcher accepts only the supported original BOOT2 ELF and creates a new ISO without modifying the source image.
- The user reports testing on a physical PS2 with OPL, MX4SIO, a directly connected component-input television, and GSM OFF. The title, HOW TO PLAY, song selection, gameplay, key judgement, and extended operation were checked. This result applies to that setup.
- See `README.md`, `README.ja.md`, and `checksums.txt` for application steps, supported hashes, and limitations.

## License and notice

The project's original source code and documentation are licensed under the MIT License; see `LICENSE`. No game data are included. This is an unofficial fan patch and is not endorsed or supported by Konami.
