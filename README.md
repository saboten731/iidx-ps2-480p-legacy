# beatmania IIDX 3rd Style 480p Patch v1.0

An unofficial fan patch for the PlayStation 2 release of *beatmania IIDX 3rd Style*, product code `SLPM_650.06`. Version 1.0 vertically doubles the game's existing 240-line image for 480p output and has been tested on a physical PS2 in the setup described below.

## Release scope

- **3rd Style v1.0:** the only patch included and supported here; hardware-tested as described in [Hardware verification](#hardware-verification).
- **4th–8th Style:** planned for separate, title-specific analysis and validation. No patches for these Styles are included or supported by v1.0.

This does not convert the game to native 640×480 rendering. The patch uses the GS display circuit to double the game's 240 rendered lines to 480 output lines. This is different from the native 480p rendering path used by patches for Style 9th and later.

## Files

- `patch480p.py`: a Python 3 patcher that inspects an ISO9660 image and writes a separate output ISO.
- `IIDX03_SLPM-65006_480p_v1.0.xdelta`: a VCDIFF/xdelta3 patch for the verified reference ISO. Download it from the [GitHub Releases page](https://github.com/saboten731/iidx-ps2-480p-legacy/releases), attached to the v1.0 Release. It is not stored in the source repository.
- `checksums.txt`: SHA-256 values for the reference ISO, patched ISO, xdelta patch, and Python output from the reference ISO.

No ISO, ELF, IRX, BIOS, or game assets are included. Use an ISO dumped from your own disc.

Before patching, keep a backup of the source ISO and record its SHA-256 for comparison with `checksums.txt`. The Python patcher leaves the source unchanged and writes a new output file.

## Supported revision

The Python patcher reads `BOOT2` from `SYSTEM.CNF`, locates the executable in the ISO9660 directory tree, and verifies product code `SLPM_650.06` plus the exact hash of the unmodified executable:

```text
Supported original BOOT2 ELF SHA-256:
CD2EE5A1C50C46808927EF32A7FE8F5791AE66399DA029A75D5095CA70499321
```

The Python patcher does not require a fixed whole-ISO SHA-256, total size, or executable sector. It accepts a different ISO hash when the dynamically located BOOT2 ELF matches the supported SHA-256 exactly. Unknown, modified, or recognized already-patched ELFs are rejected before an output is created. It never applies a patch based on a partial instruction match.

A rebuilt ISO may still have boot or compatibility issues even when its ELF matches. The patcher preserves every input byte outside the explicitly allowed ELF ranges and verifies that with a chunked comparison.

## Apply the xdelta patch

Download `IIDX03_SLPM-65006_480p_v1.0.xdelta` from the [GitHub Releases page](https://github.com/saboten731/iidx-ps2-480p-legacy/releases) and select the v1.0 Release. The patch is for the following verified reference image only. We have not verified that this image matches Redump, so no Redump claim is made.

```text
SLPM_650.06.Beatmania IIDX 3rd Style.iso
Size:   3,810,918,400 bytes
SHA256: D7E11CD70100675A97DDD9027D1578BDA1397959FA1562151BA9C9E7F94E16D1
```

Install `xdelta3`, make sure the output path does not exist, then run:

```powershell
xdelta3 -d -s "SLPM_650.06.Beatmania IIDX 3rd Style.iso" `
  "IIDX03_SLPM-65006_480p_v1.0.xdelta" `
  "SLPM_650.06.Beatmania IIDX 3rd Style_480p_v1.0.iso"
```

Verify that the resulting ISO SHA-256 matches the patched-image value in `checksums.txt`. Do not use this xdelta patch if the source image hash differs.

## Apply the Python patch

Requires Python 3.8 or newer. The input ISO is not modified. By default, the patcher adds `_480p_v1.0.iso` to the input filename. If the output already exists, it stops without overwriting it.

```powershell
python patch480p.py "SLPM_650.06.Beatmania IIDX 3rd Style.iso" `
  --output "SLPM_650.06.Beatmania IIDX 3rd Style_480p_v1.0.iso"
```

The patcher reads the `BOOT2` path from `SYSTEM.CNF` and uses the ELF extent found in the ISO. The whole-ISO SHA-256 and size are not acceptance conditions. At completion it prints input/output hashes, output size, and the patched ELF hash.

## v1.0 patch details

- Display: `DISPLAY=0x001DF4FF0882B138` (240 rendered lines doubled to 480 output lines).
- Video synchronization configuration: `SYNCV=0x00C7900001E00006` (`VDP=484`).
- RGB/component selection: preserves the existing runtime path that reads the BIOS/OSD setting. Behavior with untested OSD and display settings is not guaranteed.
- PMODE: does not read PMODE back from the GS; the game's original display-environment path restores it.
- No changes to SPU/IOP, audio pitch, chart timer, or judgement processing.

## Hardware verification

The user reports successful testing on a physical PS2 connected directly to a component-input television, using OPL and MX4SIO with GSM OFF. The user verified the title, HOW TO PLAY, song selection, actual play, key judgement, and extended operation. This result applies to that setup only; other televisions, OSD output settings, and boot methods are not guaranteed.

## Prior work

The distribution layout was informed by [blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p). That project primarily targets native 480p rendering in Styles 9th–16th; this 3rd Style patch uses a different title and display path. No patch code from that repository is included here.

## License

This project's original source code and documentation are licensed under the MIT License; see [LICENSE](LICENSE). This license does not grant rights to Konami's game, game assets, or trademarks. No game data are included in this repository or Release.

## Unofficial notice

This is an unofficial fan patch and is not an official Konami product. It is not endorsed or supported by Konami. Own the game and ensure that applying the patch is permitted by applicable law and local rules.
