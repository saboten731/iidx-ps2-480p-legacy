# IIDX 3rd Style 480p Patch v1.0 (Draft)

This draft release contains the v1.0 patch for the PlayStation 2 version of beatmania IIDX 3rd Style, product code `SLPM_650.06`.

## What it does

- Vertically doubles the game's existing 240-line image to produce 480p output. It does not change the game to native 640x480 rendering.
- Uses `DISPLAY=0x001DF4FF0882B138` and the verified video synchronization configuration `SYNCV=0x00C7900001E00006` (`VDP=484`).
- Preserves runtime BIOS/OSD color selection and the game's PMODE restoration path.
- Does not add audio, chart-timer, or judgement compensation.

## Compatibility and verification

- Supported title: 3rd Style, `SLPM_650.06` only. Other Styles are not supported by this release.
- The xdelta asset applies only to the verified reference ISO whose SHA-256 is recorded in `checksums.txt`.
- The Python patcher accepts only an allowlisted original BOOT2 ELF and writes a separate ISO.
- Hardware testing was reported by the user on a physical PS2 with OPL, MX4SIO, a directly connected component-input TV, and GSM OFF. The title, HOW TO PLAY, song selection, gameplay, judgement, and extended operation were checked.
- No ISO, ELF, BIOS, IRX, or other game data is included.

See `README.md`, `README.ja.md`, and `checksums.txt` for application instructions, limitations, and hashes.

## Draft status

The project's source license has not yet been selected. This release remains a draft pending review of the license, bilingual notes, README, and attached xdelta hash. This is an unofficial fan project and is not endorsed by Konami.
