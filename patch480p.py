#!/usr/bin/env python3
"""Patch a supported IIDX PS2 ISO to its title-specific 480p profile.

Only the exact allowlisted BOOT2 ELF is accepted. The ISO and boot ELF extents
are read from ISO9660/SYSTEM.CNF; the input image itself is never modified.
Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import struct
import sys
from pathlib import Path


SECTOR_SIZE = 2048
# Reject known development outputs explicitly instead of treating them as a
# supported original revision. Other modified ELFs are rejected by the allowlist.
ALREADY_PATCHED_ELF_SHA256S = {
    "CFBFC4BA81CEF34EA021100FCD42F34F224AE95AD7B71D5423F59C2612DABF8A",
    "1300A2CF006F401358F5115769F8E6889805AC5D79EE4993B620AED1E3ADD449",
    "B15A3794774CDBF4F50051CA1FC8BB630D71FE815AE5B7B70A8F19709CF49362",
    "37324FAAC44995287B365F7D20CE732F97955731ADB1B8D35EE4CFD46F7DB681",
    "0FB400A107B64CB4D1034A2523FAE6019E4ACAF72BDCD0B11687CBF0F9C43784",
    "D0B0239D88BC055D7888CD15A1DBB6B14F020CF2D8CF32DA8E9BAE0B3E7B2A8B",
    "4FC4BEA6C4A1DBCECBE245CE5C9398E89BE36977628EF88F3F0EB4E668ECC6B4",
    "7134FF3E2FE82EE047AE211E1CC8ADEF60651F30EEE56142C0557737002F8875",
    "92DA7BE55F2D8E70B6E9E6A799ECE67C15E7D9AB41C80B5ED90B9A467321B7CB",
    "6AFA8792C1FD1A177D807D73324AAFA23B506FEC635C50A834D2703761A896BD",
    "106F4482FA6DECA1D8A0412F85AFC2E8CE265EBE0FFACD79BF5CEB649F4855E2",
    "833129A3A1EC9EE3F45816377336681D565706F4559A65902FD071B34CCEFC56",
}
MAX_BOOT_ELF_SIZE = 128 * 1024 * 1024  # Defensive parser limit, not a revision check.
MIN_OUTPUT_SPACE_MARGIN = 64 * 1024 * 1024

GS_BASE = 0x12000000
GS_PMODE_OFFSET = 0x00
GS_SMODE1_OFFSET = 0x10
GS_SMODE2_OFFSET = 0x20
GS_SRFSH_OFFSET = 0x30
GS_SYNCH1_OFFSET = 0x40
GS_SYNCH2_OFFSET = 0x50
GS_SYNCV_OFFSET = 0x60

# Preserve the previously observed 480p SMODE1 profile's non-control fields.
# PRST (bit 16) and SINT (bit 17) are clear in the final profile. GCONT (bit
# 25) is ORed from ConfigParam.videoOutput at runtime, never fixed in the ISO.
SMODE1_PROFILE_FINAL = 0x0000001740400504
SMODE1_GCONT = 1 << 25
SMODE1_PRST = 1 << 16
SMODE1_SINT = 1 << 17
CONFIG_VIDEO_OUTPUT_SHIFT = 3

CRTC_REGISTER_OFFSETS = (
    GS_SMODE2_OFFSET,
    GS_SRFSH_OFFSET,
    GS_SYNCH1_OFFSET,
    GS_SYNCH2_OFFSET,
    GS_SYNCV_OFFSET,
)

PATCH_PROFILES = {
    "v1.0": {
        "display_value": 0x001DF4FF0882B138,
        # BIOS-native VDP+1 needs per-BIOS values: inspected SYNCV defaults
        # differ (10000 VDP=483/VFP=6; 39001/77000 VDP=480/VFP=9).
        "timing_values": (
            0x0000000000000002,  # SMODE2
            0x0000000000000004,  # SRFSH
            0x000402DA20034020,  # SYNCH1
            0x000000000019D272,  # SYNCH2
            0x00C7900001E00006,  # SYNCV: published VDP=484 profile
        ),
    },
}

# Per-title identities and patch locations are kept separate. Every executable
# is independently allowlisted by its unmodified BOOT2 ELF SHA-256; addresses
# and caves must never be inferred from the neighboring Style.
TITLE_CONFIGS = {
    "SLPM_650.06": {
        "title": "IIDX 3rd Style",
        "state": "PATCHED_IIDX03_480P_V1_0",
        "elf_sha256": "CD2EE5A1C50C46808927EF32A7FE8F5791AE66399DA029A75D5095CA70499321",
        "patched_elf_sha256": "12CC9C5F6DA5AB7581BFD5B5C9F185BAB80EC2C649303CE6D4ACDB825DA83292",
        "load_segment": (0x1000, 0x00100000, 0x0089E249, 0x00CC518C, 0x7),
        "text": (0x00100000, 0x1000, 0x000765EC),
        "display_cave_va": 0x00171808,
        "display_cave_size": 0x3A,
        "display_helper_size": 0x28,  # Original helper occupies 40 of 58 safe cave bytes.
        "display_cave_section": ".text",
        "display_scan_pointer_range": False,  # Packed assets contain an aligned 0x00171819 data word.
        "crtc_cave_va": 0x002A3980,
        "crtc_cave_size": 0x118,
        "display_hook_va": 0x001581C0,
        "display_hook_delay_va": 0x001581C4,
        "display_hook_return_va": 0x001581C8,
        "resetgraph_tail_va": 0x00157378,
        "resetgraph_delay_va": 0x0015737C,
        "resetgraph_delay_word": 0x27BD0080,
        "setgscrt_wrapper_va": 0x00171860,
        "mode_patches": (
            (0x001001FC, 0x24060002, 0x24060050, "boot ResetGraph: NTSC to DTV 480p"),
            (0x0014F8BC, 0x24060002, 0x24060050, "game ResetGraph: NTSC to DTV 480p"),
            (0x00158018, 0x24040002, 0x24040050, "DISPLAY environment mode to DTV480P"),
        ),
        "pmode_checks": (
            (0x00157FDC, 0x24020066, "display-environment PMODE value"),
            (0x00157FE0, 0xFE220000, "store PMODE at display-env offset 0"),
            (0x00157460, 0xFC440000, "write PMODE in branch 1"),
            (0x001574A0, 0xFC640000, "write PMODE in branch 2"),
            (0x00157684, 0x0C055FE2, "first environment uses PMODE builder"),
            (0x001576A0, 0x0C055FE2, "second environment uses PMODE builder"),
            (0x0014F534, 0x08055D0C, "display update tail-calls GS writer"),
            (0x0014FC7C, 0x08055D0C, "alternate display update tail-calls GS writer"),
            (0x001578C8, 0x0C055D0C, "environment update calls GS writer"),
        ),
    },
    "SLPM_650.26": {
        "title": "IIDX 4th Style",
        "state": "PATCHED_IIDX04_480P_HARDWARE_PASS",
        "elf_sha256": "DC507D7D35A7AF5ADB1607B856FCC23AAF8CB6841B32EC53266C3741F6A35429",
        "patched_elf_sha256": "9E4DBDBBC577991F5D115B679DCDB138F282E8AB69A99969C0774C0FB6F78484",
        "load_segment": (0x1000, 0x00100000, 9_251_545, 13_623_500, 0x7),
        "text": (0x00100000, 0x1000, 0x000893E0),
        "display_cave_va": 0x00278520,
        "display_cave_size": 0x28,
        "crtc_cave_va": 0x00278400,
        "crtc_cave_size": 0x118,
        "display_hook_va": 0x001697D8,
        "display_hook_delay_va": 0x001697DC,
        "display_hook_return_va": 0x001697E0,
        "resetgraph_tail_va": 0x001689A4,
        "resetgraph_delay_va": 0x001689A8,
        "setgscrt_wrapper_va": 0x001839E0,
        "mode_patches": (
            (0x00100204, 0x24060002, 0x24060050, "startup ResetGraph mode 2 to DTV480P"),
            (0x00160A64, 0x24060002, 0x24060050, "game ResetGraph mode 2 to DTV480P"),
            (0x00169628, 0x24040002, 0x24040050, "DISPLAY environment mode 2 to DTV480P"),
        ),
        "pmode_checks": (
            (0x00168A70, 0xDE040000, "load PMODE from IIDX display environment"),
            (0x00168A80, 0xFC440000, "write IIDX-owned PMODE in DISPLAY1 path"),
            (0x00168AB4, 0x3C031200, "DISPLAY2 path GS base"),
            (0x00168AC0, 0xFC640000, "write IIDX-owned PMODE in DISPLAY2 path"),
        ),
    },
    "SLPM_650.49": {
        "title": "IIDX 5th Style",
        "state": "PATCHED_IIDX05_480P_HARDWARE_PASS",
        "elf_sha256": "6667292D88836087A90BEDD8E9856AE08132FDC4291D4958DDBE11E37F547B9C",
        "patched_elf_sha256": "68054D4B48C863F5316785BC038D0E9515EEDDA1AA55BAA3FFFC421C055CB481",
        "load_segment": (0x1000, 0x00100000, 13_639_337, 18_059_020, 0x7),
        "text": (0x00100000, 0x1000, 0x000ABE88),
        "display_cave_va": 0x00464D40,
        "display_cave_size": 0x28,
        "crtc_cave_va": 0x00464C20,
        "crtc_cave_size": 0x118,
        "display_hook_va": 0x0018A100,
        "display_hook_delay_va": 0x0018A104,
        "display_hook_return_va": 0x0018A108,
        "resetgraph_tail_va": 0x001892CC,
        "resetgraph_delay_va": 0x001892D0,
        "setgscrt_wrapper_va": 0x001A3B60,
        "mode_patches": (
            (0x00100208, 0x24060002, 0x24060050, "startup ResetGraph mode 2 to DTV480P"),
            (0x00181334, 0x24060002, 0x24060050, "game ResetGraph mode 2 to DTV480P"),
            (0x00189F50, 0x24040002, 0x24040050, "DISPLAY environment mode 2 to DTV480P"),
        ),
        "pmode_checks": (
            (0x00189398, 0xDE040000, "load PMODE from IIDX display environment"),
            (0x001893A8, 0xFC440000, "write IIDX-owned PMODE in DISPLAY1 path"),
            (0x001893DC, 0x3C031200, "DISPLAY2 path GS base"),
            (0x001893E8, 0xFC640000, "write IIDX-owned PMODE in DISPLAY2 path"),
        ),
    },
    "SLPM_651.56": {
        "title": "IIDX 6th Style",
        "state": "PATCHED_IIDX06_480P_HARDWARE_DISPLAY_AND_PLAY_PASS",
        "elf_sha256": "4C58566CD7D5E5F0EBA377615EB27FA87E8E2EA99C10673D619DCF4693EA751B",
        "patched_elf_sha256": "94F0B6B2B6167D842ED34C3A202DF2839E2B50E922121A8A2F209905ECC3C240",
        "load_segments": (
            (0x1000, 0x00100000, 847_440, 847_440, 0x5),
            (851_584, 1_896_064, 8_884_236, 14_588_912, 0x6),
        ),
        "text": (0x00100000, 0x1000, 847_416),
        "display_cave_va": 0x002E9120,
        "display_cave_size": 0xF0,
        "display_cave_section": ".rodata",
        "display_cave_executable": False,
        "crtc_cave_va": 0x004E6DC0,
        "crtc_cave_size": 0x118,
        "crtc_cave_section": ".rodata",
        "crtc_cave_executable": False,
        "resetgraph_tails": (
            (0x001A9E90, 0x001A9E94),
            (0x001A9F08, 0x001A9F0C),
        ),
        "setgscrt_wrapper_va": 0x001C5760,
        "mode_patches": (
            (0x0010020C, 0x24060002, 0x24060050, "startup ResetGraph mode 2 to DTV480P"),
            (0x001A1640, 0x24060002, 0x24060050, "game ResetGraph mode 2 to DTV480P"),
            (0x001AAB78, 0x24040002, 0x24040050, "DISPLAY environment mode 2 to DTV480P"),
        ),
        "pmode_checks": (
            (0x001A9FC0, 0xDE040000, "load PMODE from IIDX display environment"),
            (0x001A9FD0, 0xFC440000, "write IIDX-owned PMODE in DISPLAY1 path"),
            (0x001AA004, 0x3C031200, "DISPLAY2 path GS base"),
            (0x001AA010, 0xFC640000, "write IIDX-owned PMODE in DISPLAY2 path"),
        ),
        "display_hooks": (
            (0x001A9FF0, 0x001A9FF4, 0xFCC20000, 0xDE030020, 0x00, 0x001A9FF8, "v0", "a2"),
            # 0x001AA038 writes DISPFB2 (0x12000090); DISPLAY2 is the next store.
            (0x001AA040, 0x001AA044, 0xFCA30000, 0xDE020020, 0x18, 0x001AA048, "v1", "a1"),
        ),
        "display_mode": "dynamic_240_or_224_rows",
        # Hardware-validated 6th path: double 256 source rows, display 480.
        "display_scale_256_rows": True,
        "display_256_to_480": True,
        "display_256_dy_plus18": True,
        "display_256_horizontal_fix": True,
    },
    "SLPM_655.93": {
        "title": "IIDX 7th Style",
        "state": "PATCHED_IIDX07_480P_HARDWARE_DISPLAY_AND_PLAY_PASS",
        "elf_sha256": "A0D1D4C1C47F0A251F7708DC003EE4A86A3D4FDC194BF9A6EEDA4B96063CCCEC",
        "patched_elf_sha256": "F1EF5509C9706A763DE54F72B8B3DEBB1F5E68A6B735EBFCAE6787251D0D3120",
        "load_segments": (
            (128, 0x00100000, 11_714_944, 17_513_600, 0x7),
            (11_715_072, 18_562_176, 0, 0, 0x6),
        ),
        "stripped": True,
        "static_section_safety": False,
        "crtc_cave_va": 0x002D8464,
        "crtc_cave_size": 0x118,
        "display_cave_va": 0x001F0630,
        "display_cave_size": 0x90,
        "resetgraph_tails": (
            (0x00100450, 0x00100454),
            (0x001004C8, 0x001004CC),
        ),
        "setgscrt_wrapper_va": 0x0010DD60,
        "mode_patches": (
            (0x0012AA40, 0x24060002, 0x24060050, "startup ResetGraph mode 2 to DTV480P"),
        ),
        "pmode_checks": (
            (0x001009A8, 0xDE040000, "load IIDX-owned PMODE from display environment"),
            (0x001009B8, 0xFC440000, "write IIDX-owned PMODE in DISPLAY1 path"),
            (0x001009EC, 0x3C031200, "DISPLAY2 path GS base"),
            (0x001009F8, 0xFC640000, "write IIDX-owned PMODE in DISPLAY2 path"),
        ),
        "display_hooks": (
            (0x001009D8, 0x001009DC, 0xFCC20000, 0xDE030020, 0x00, 0x001009E0, "v0", "a2"),
            (0x00100A28, 0x00100A2C, 0xFCA30000, 0xDE020020, 0x18, 0x00100A30, "v1", "a1"),
        ),
        "display_mode": "dynamic_240_or_224_rows",
        # ResetGraph mode 80 builds 640x256 DISPLAY with suitable horizontal
        # fields; scale only that verified input. Other modes pass through.
        "display_scale_256_rows": True,
        "display_256_to_480": True,
        "display_only_256_rows": True,
        "display_256_dy_plus8": True,
        "crtc_cave_guard": (0x002D845C, 0x00000000, 0x002D8460, 0x00000000),
        "crtc_cave_guard_source": (0x002E0FC8, 0x5290DD24),
    },
    "SLPM_657.68": {
        "title": "IIDX 8th Style",
        "state": "PATCHED_IIDX08_480P_HARDWARE_PASS",
        "elf_sha256": "F4EFE03117DF8F31B0B23AE8D9A963F9D60FFE6D9CD7EFE4A7B0A5CAD925B220",
        "patched_elf_sha256": "C7E562C6CBEB471EAC8B575596354FCD19574662F15E08F2CBA88EE61510630E",
        "load_segments": (
            (128, 0x00100000, 9_893_504, 15_628_928, 0x7),
            (9_893_632, 16_677_504, 0, 0, 0x6),
        ),
        "stripped": True,
        "static_section_safety": False,
        "crtc_cave_va": 0x0021D810,
        "crtc_cave_size": 0xF8,
        "display_cave_va": 0x0021D908,
        "display_cave_size": 0x90,
        "resetgraph_tails": (
            (0x001003C0, 0x001003C4),
            (0x00100438, 0x0010043C),
        ),
        "setgscrt_wrapper_va": 0x0010DCA0,
        "mode_patches": (
            (0x0012AF00, 0x24060002, 0x24060050, "startup ResetGraph mode 2 to DTV480P"),
        ),
        "pmode_checks": (
            (0x00100918, 0xDE040000, "load IIDX-owned PMODE from display environment"),
            (0x00100928, 0xFC440000, "write IIDX-owned PMODE in DISPLAY1 path"),
            (0x0010095C, 0x3C031200, "DISPLAY2 path GS base"),
            (0x00100968, 0xFC640000, "write IIDX-owned PMODE in DISPLAY2 path"),
        ),
        "display_hooks": (
            (0x00100948, 0x0010094C, 0xFCC20000, 0xDE030020, 0x00, 0x00100950, "v0", "a2"),
            (0x00100998, 0x0010099C, 0xFCA30000, 0xDE020020, 0x18, 0x001009A0, "v1", "a1"),
        ),
        "display_mode": "dynamic_240_or_224_rows",
        # ResetGraph mode 80 reaches the 640x256 builder. Scale only its
        # verified MAGV=0,DH=255 input; retain DY and horizontal fields.
        "display_scale_256_rows": True,
        "display_256_to_480": True,
        "display_only_256_rows": True,
        "display_256_dy_plus8": True,
        # Existing diagnostics inspect this key directly; share the one profile tuple.
        "timing_values": PATCH_PROFILES["v1.0"]["timing_values"],
    },
}

ALREADY_PATCHED_ELF_SHA256S.update(
    config["patched_elf_sha256"] for config in TITLE_CONFIGS.values()
)

# Compatibility fallbacks used by existing tests' dict.get defaults. Patch
# generation reads the selected title's cave addresses from TITLE_CONFIGS.
CRTC_CAVE_VA = TITLE_CONFIGS["SLPM_650.06"]["crtc_cave_va"]
CRTC_CAVE_SIZE = TITLE_CONFIGS["SLPM_650.06"]["crtc_cave_size"]

SYSCALL_SETGSCRT = 0x02
SYSCALL_GETOSDCONFIGPARAM = 0x4B
SYSCALL_SETGSVPARAM = 0x4F
SYNC_L_WORD = 0x0000000F  # SPECIAL, stype=0, funct=SYNC
SYNC_P_WORD = 0x0000040F  # SPECIAL, stype=16, funct=SYNC

REG = {
    "zero": 0, "v0": 2, "v1": 3,
    "a0": 4, "a1": 5, "a2": 6,
    "t0": 8, "t1": 9, "t2": 10, "t3": 11, "t4": 12,
    "t7": 15, "t8": 24, "t9": 25,
    "sp": 29, "ra": 31,
}


class PatchError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_at(stream, offset: int, length: int) -> bytes:
    stream.seek(offset)
    data = stream.read(length)
    if len(data) != length:
        raise PatchError(f"short read at ISO offset {offset:#x}")
    return data


def parse_directory(data: bytes):
    pos = 0
    while pos < len(data):
        record_size = data[pos]
        if record_size == 0:
            pos = ((pos // SECTOR_SIZE) + 1) * SECTOR_SIZE
            continue
        record = data[pos : pos + record_size]
        if len(record) != record_size or record_size < 34:
            raise PatchError("malformed ISO9660 directory record")
        name_size = record[32]
        name = record[33 : 33 + name_size].decode("ascii", errors="strict")
        if name == "\x00":
            name = "."
        elif name == "\x01":
            name = ".."
        lba = struct.unpack_from("<I", record, 2)[0]
        length = struct.unpack_from("<I", record, 10)[0]
        is_directory = bool(record[25] & 2)
        yield name, lba, length, is_directory
        pos += record_size


def _read_iso_extent(stream, iso_size: int, lba: int, length: int, label: str) -> bytes:
    if lba < 0 or length <= 0:
        raise PatchError(f"invalid ISO9660 extent for {label}")
    offset = lba * SECTOR_SIZE
    if offset + length > iso_size:
        raise PatchError(f"ISO9660 extent for {label} lies outside the image")
    return read_at(stream, offset, length)


def _lookup_iso_entry(entries, requested_name: str, label: str):
    key = requested_name.split(";", 1)[0].upper()
    matches = [
        entry
        for entry in entries
        if entry[0] not in (".", "..") and entry[0].split(";", 1)[0].upper() == key
    ]
    if not matches:
        raise PatchError(f"ISO9660 entry for {label} was not found: {requested_name}")
    if len(matches) != 1:
        raise PatchError(f"ambiguous ISO9660 entries for {label}: {requested_name}")
    return matches[0]


def locate_boot_elf(
    iso_path: Path, *, verify_original_elf: bool = True
) -> tuple[int, int, bytes, str]:
    iso_size = iso_path.stat().st_size
    if iso_size < 17 * SECTOR_SIZE:
        raise PatchError("file is too small to contain an ISO9660 primary volume descriptor")

    with iso_path.open("rb") as stream:
        pvd = read_at(stream, 16 * SECTOR_SIZE, SECTOR_SIZE)
        if pvd[:7] != b"\x01CD001\x01":
            raise PatchError("ISO9660 primary volume descriptor not found")
        root_size = pvd[156]
        root_record = pvd[156 : 156 + root_size]
        if root_size < 34 or len(root_record) != root_size:
            raise PatchError("invalid ISO9660 root directory record")
        root_lba = struct.unpack_from("<I", root_record, 2)[0]
        root_len = struct.unpack_from("<I", root_record, 10)[0]
        if root_len > 64 * 1024 * 1024:
            raise PatchError("ISO9660 root directory exceeds the safety limit")
        root_data = _read_iso_extent(stream, iso_size, root_lba, root_len, "root directory")
        root_entries = list(parse_directory(root_data))
        system_cnf = _lookup_iso_entry(root_entries, "SYSTEM.CNF;1", "SYSTEM.CNF")
        if system_cnf[3]:
            raise PatchError("SYSTEM.CNF is a directory")
        cnf_data = _read_iso_extent(stream, iso_size, system_cnf[1], system_cnf[2], "SYSTEM.CNF")
        if len(cnf_data) > 1024 * 1024:
            raise PatchError("SYSTEM.CNF exceeds the safety limit")
        try:
            cnf = cnf_data.decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise PatchError("SYSTEM.CNF is not ASCII text") from exc

        match = re.search(
            r"^\s*BOOT2\s*=\s*cdrom0:(.*?)\s*$",
            cnf,
            re.MULTILINE | re.IGNORECASE,
        )
        if not match:
            raise PatchError("BOOT2 path was not found in SYSTEM.CNF")
        boot_path = match.group(1).strip().strip('"').replace("/", "\\")
        components = [part for part in boot_path.split("\\") if part]
        if not components or ".." in components:
            raise PatchError("BOOT2 path is empty or contains parent traversal")
        if len(components) > 16:
            raise PatchError("BOOT2 path exceeds the directory-depth safety limit")
        product_code = components[-1].split(";", 1)[0].upper()
        if product_code not in TITLE_CONFIGS:
            raise PatchError(f"unsupported BOOT2 executable: {components[-1]}")

        current_entries = root_entries
        for component in components[:-1]:
            entry = _lookup_iso_entry(current_entries, component, "BOOT2 directory")
            if not entry[3]:
                raise PatchError(f"BOOT2 path component is not a directory: {component}")
            directory = _read_iso_extent(stream, iso_size, entry[1], entry[2], component)
            if len(directory) > 64 * 1024 * 1024:
                raise PatchError(f"BOOT2 directory exceeds the safety limit: {component}")
            current_entries = list(parse_directory(directory))

        boot_entry = _lookup_iso_entry(current_entries, components[-1], "BOOT2 executable")
        if boot_entry[3]:
            raise PatchError("BOOT2 target is a directory")
        elf_lba, elf_size = boot_entry[1], boot_entry[2]
        if elf_size <= 0 or elf_size > MAX_BOOT_ELF_SIZE:
            raise PatchError(f"BOOT2 ELF size is outside the safety limit: {elf_size}")
        elf_offset = elf_lba * SECTOR_SIZE
        elf = _read_iso_extent(stream, iso_size, elf_lba, elf_size, "BOOT2 ELF")

    if verify_original_elf:
        elf_hash = sha256_bytes(elf)
        if elf_hash in ALREADY_PATCHED_ELF_SHA256S:
            raise PatchError("BOOT2 ELF is already patched; refusing double application")
        expected_elf_hash = TITLE_CONFIGS[product_code]["elf_sha256"]
        if elf_hash != expected_elf_hash:
            raise PatchError(
                "unsupported or modified BOOT2 ELF SHA-256 "
                f"{elf_hash}; {product_code} requires the allowlisted "
                f"{expected_elf_hash} revision"
            )
    return elf_offset, elf_size, elf, product_code


def parse_title_load_segment(elf: bytes, product_code: str):
    """Parse and exactly verify every PT_LOAD for one title."""
    if product_code not in TITLE_CONFIGS:
        raise PatchError(f"unsupported title profile: {product_code}")
    if elf[:6] != b"\x7fELF\x01\x01":
        raise PatchError("boot executable is not ELF32 little-endian")
    fields = struct.unpack_from("<HHIIIIIHHHHHH", elf, 16)
    phoff, phentsize, phnum = fields[4], fields[8], fields[9]
    if phentsize < 32 or phoff + phentsize * phnum > len(elf):
        raise PatchError("invalid ELF program header table")
    loads = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, p_off, p_va, _p_pa, p_filesz, p_memsz, p_flags, _p_align = struct.unpack_from(
            "<IIIIIIII", elf, off
        )
        if p_type == 1:
            loads.append((p_off, p_va, p_filesz, p_memsz, p_flags))
    config = TITLE_CONFIGS[product_code]
    expected = (
        tuple(config["load_segments"])
        if "load_segments" in config
        else (config["load_segment"],)
    )
    if tuple(loads) != expected:
        raise PatchError(f"unexpected {product_code} PT_LOAD layout: {loads!r}")
    return tuple(loads)


def parse_sections(elf: bytes) -> dict[str, tuple[int, int, int, int]]:
    if len(elf) < 0x34 or elf[:6] != b"\x7fELF\x01\x01":
        raise PatchError("cannot inspect sections of a non-ELF32 little-endian file")
    shoff = struct.unpack_from("<I", elf, 0x20)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", elf, 0x2E)
    if shentsize < 40 or shnum == 0 or shstrndx >= shnum:
        raise PatchError("invalid ELF section table")
    if shoff + shentsize * shnum > len(elf):
        raise PatchError("ELF section table lies outside the executable")
    headers = [
        struct.unpack_from("<IIIIIIIIII", elf, shoff + i * shentsize)
        for i in range(shnum)
    ]
    strings = headers[shstrndx]
    names = elf[strings[4] : strings[4] + strings[5]]
    result = {}
    for header in headers:
        name_off, _typ, flags, address, file_off, size, *_ = header
        if name_off >= len(names):
            continue
        end = names.find(b"\0", name_off)
        if end < 0:
            raise PatchError("unterminated ELF section name")
        name = names[name_off:end].decode("ascii", errors="strict")
        if name:
            result[name] = (flags, address, file_off, size)
    return result


def va_to_file_offset(va: int, length: int, segment, *, require_executable: bool = True) -> int:
    """Map a VA through one or more verified PT_LOADs."""
    if len(segment) == 5 and isinstance(segment[0], int):
        segments = (segment,)
    else:
        segments = tuple(segment)
    matches = []
    non_executable_match = False
    for p_off, p_va, p_filesz, _p_memsz, p_flags in segments:
        rel = va - p_va
        if rel < 0 or rel + length > p_filesz:
            continue
        if require_executable and (p_flags & 1) == 0:
            non_executable_match = True
            continue
        matches.append(p_off + rel)
    if len(matches) > 1:
        raise PatchError(f"VA range {va:#x}+{length:#x} maps through multiple PT_LOADs")
    if matches:
        return matches[0]
    if non_executable_match:
        raise PatchError(f"VA range {va:#x}+{length:#x} is not in an executable PT_LOAD")
    raise PatchError(f"VA range {va:#x}+{length:#x} is outside file-backed PT_LOAD")


def title_patch_va_to_file_offset(va: int, length: int, segment, title_config: dict) -> int:
    """Map a verified cave; only title-declared non-executable caves may bypass PF_X."""
    require_executable = True
    for cave_name in ("display", "crtc"):
        if va == title_config.get(f"{cave_name}_cave_va"):
            require_executable = title_config.get(f"{cave_name}_cave_executable", True)
            break
    return va_to_file_offset(
        va, length, segment, require_executable=require_executable
    )


def encode_j(pc: int, target: int) -> int:
    if ((pc + 4) >> 28) != (target >> 28):
        raise PatchError(f"MIPS J target {target:#x} is out of range from {pc:#x}")
    return 0x08000000 | ((target >> 2) & 0x03FFFFFF)


def encode_i(op: int, rs: int, rt: int, imm: int) -> int:
    if not -0x8000 <= imm <= 0xFFFF:
        raise PatchError(f"MIPS immediate out of range: {imm:#x}")
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


def encode_r(rs: int, rt: int, rd: int, sa: int, fn: int) -> int:
    return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn


def build_crtc_helper(
    timing_values: tuple[int, ...],
    cave_va: int,
) -> tuple[bytes, list[tuple[str, int]], int]:
    """Assemble a straight-line R5900 helper and append its aligned data table."""
    if SMODE1_PROFILE_FINAL & (SMODE1_PRST | SMODE1_SINT):
        raise PatchError("final SMODE1 must have PRST and SINT cleared")
    code: list[int] = []
    listing: list[tuple[str, int]] = []
    events: dict[str, int] = {}

    def emit(text: str, word: int, event: str | None = None) -> None:
        if event:
            events[event] = len(code)
        code.append(word & 0xFFFFFFFF)
        listing.append((text, word & 0xFFFFFFFF))

    def ri(op: int, rt: str, rs: str, imm: int, text: str) -> None:
        emit(text, encode_i(op, REG[rs], REG[rt], imm))

    def rr(rs: str, rt: str, rd: str, sa: int, fn: int, text: str) -> None:
        emit(text, encode_r(REG[rs], REG[rt], REG[rd], sa, fn))

    # ResetGraph's delay slot has already restored its incoming stack. Save the
    # two SetGsCrt arguments needed after the OSD/SetGsVParam syscalls.
    ri(0x19, "sp", "sp", -32, "daddiu sp,sp,-32")
    ri(0x2B, "a0", "sp", 0x18, "sw a0,24(sp)")
    ri(0x2B, "a2", "sp", 0x1C, "sw a2,28(sp)")

    # GetOsdConfigParam(ConfigParam*) uses syscall 0x4B. videoOutput is bit 3
    # of the first ConfigParam word (0=RGB, 1=COMPONENT).
    ri(0x09, "a0", "sp", 0, "addiu a0,sp,0")
    ri(0x09, "v1", "zero", SYSCALL_GETOSDCONFIGPARAM, "addiu v1,zero,0x4b")
    emit("syscall", 0x0000000C)
    ri(0x23, "t0", "sp", 0, "lw t0,0(sp)")
    ri(0x0C, "a0", "t0", 1 << CONFIG_VIDEO_OUTPUT_SHIFT, "andi a0,t0,0x0008")
    rr("zero", "a0", "a0", CONFIG_VIDEO_OUTPUT_SHIFT, 0x02, "srl a0,a0,3")
    ri(0x09, "v1", "zero", SYSCALL_SETGSVPARAM, "addiu v1,zero,0x4f")
    emit("syscall", 0x0000000C)

    # Match PS2SDK graph_set_mode(): order prior stores before SetGsCrt.
    emit("sync.p", SYNC_P_WORD, "sync_before_setgscrt")
    emit("nop", 0)
    ri(0x23, "a0", "sp", 0x18, "lw a0,24(sp)")
    ri(0x09, "a1", "zero", 2, "addiu a1,zero,2")  # Preserve NTSC VBlank mode.
    ri(0x23, "a2", "sp", 0x1C, "lw a2,28(sp)")
    ri(0x09, "v1", "zero", SYSCALL_SETGSCRT, "addiu v1,zero,2")
    emit("syscall", 0x0000000C)

    # GS privileged PMODE reads are not a valid software shadow (PCSX2 mirrors
    # CSR there). Disable both read circuits, then let IIDX's normal display-
    # environment writer restore the PMODE value it already owns. This avoids
    # both PMODE readback and a fixed 0x66 restoration value.
    ri(0x0F, "t0", "zero", GS_BASE >> 16, "lui t0,0x1200")
    ri(0x3F, "zero", "t0", GS_PMODE_OFFSET, "sd zero,0(t0) ; disable RC1/RC2 until IIDX writes its display env")
    events["pmode_disabled"] = len(code) - 1

    # Build the runtime SMODE1: preserve the observed profile, clear PRST and
    # SINT in the final form, then OR the live OSD GCONT bit. Keep the final
    # value in t4 while t1 is reused for timing-table loads.
    table_address_load_index = len(code)
    emit("lui t9,<timing_table_hi>", 0)
    emit("ori t9,t9,<timing_table_lo>", 0)
    ri(0x37, "t1", "t9", 0, "ld t1,0(t9) ; final SMODE1 profile")
    ri(0x23, "t2", "sp", 0, "lw t2,0(sp) ; ConfigParam")
    ri(0x0C, "t2", "t2", 1 << CONFIG_VIDEO_OUTPUT_SHIFT, "andi t2,t2,0x0008")
    rr(
        "zero", "t2", "t2",
        SMODE1_GCONT.bit_length() - 1 - CONFIG_VIDEO_OUTPUT_SHIFT,
        0x00, "sll t2,t2,22 ; videoOutput bit 3 -> GCONT bit 25",
    )
    rr("t1", "t2", "t1", 0, 0x25, "or t1,t1,t2 ; runtime GCONT")
    rr("t1", "zero", "t4", 0, 0x2D, "daddu t4,t1,zero ; retain final SMODE1")
    ri(0x0F, "t3", "zero", SMODE1_PRST >> 16, "lui t3,0x0001")
    rr("t1", "t3", "t3", 0, 0x25, "or t3,t1,t3 ; prepare PRST=1")
    ri(0x3F, "t3", "t0", GS_SMODE1_OFFSET, "sd t3,16(t0) ; SMODE1 prepare")
    events["smode1_prepare"] = len(code) - 1
    emit("sync.l", SYNC_L_WORD, "sync_after_prepare_l")
    emit("sync.p", SYNC_P_WORD, "sync_after_prepare_p")

    timing_events = []
    for table_index, register_offset in enumerate(CRTC_REGISTER_OFFSETS, start=1):
        table_off = table_index * 8
        register_name = {
            GS_SMODE2_OFFSET: "SMODE2",
            GS_SRFSH_OFFSET: "SRFSH",
            GS_SYNCH1_OFFSET: "SYNCH1",
            GS_SYNCH2_OFFSET: "SYNCH2",
            GS_SYNCV_OFFSET: "SYNCV",
        }[register_offset]
        ri(0x37, "t1", "t9", table_off, f"ld t1,{table_off}(t9) ; {register_name} value")
        ri(0x3F, "t1", "t0", register_offset, f"sd t1,{register_offset}(t0) ; {register_name}")
        event = f"write_{register_name.lower()}"
        events[event] = len(code) - 1
        timing_events.append(event)
    emit("sync.l", SYNC_L_WORD, "sync_after_timing_l")
    emit("sync.p", SYNC_P_WORD, "sync_after_timing_p")

    ri(0x3F, "t4", "t0", GS_SMODE1_OFFSET, "sd t4,16(t0) ; SMODE1 final (PRST=0,SINT=0)")
    events["smode1_final"] = len(code) - 1
    ri(0x19, "sp", "sp", 32, "daddiu sp,sp,32")
    rr("ra", "zero", "zero", 0, 0x08, "jr ra")
    emit("nop", 0)

    code_end = cave_va + len(code) * 4
    table_va = (code_end + 7) & ~7
    table_hi = (table_va >> 16) & 0xFFFF
    table_lo = table_va & 0xFFFF
    code[table_address_load_index] = encode_i(0x0F, 0, REG["t9"], table_hi)
    code[table_address_load_index + 1] = encode_i(0x0D, REG["t9"], REG["t9"], table_lo)
    listing[table_address_load_index] = (f"lui t9,0x{table_hi:04x}", code[table_address_load_index])
    listing[table_address_load_index + 1] = (f"ori t9,t9,0x{table_lo:04x}", code[table_address_load_index + 1])

    if len(timing_values) != len(CRTC_REGISTER_OFFSETS):
        raise PatchError("unexpected number of CRTC timing values")
    table_values = (SMODE1_PROFILE_FINAL, *timing_values)
    code_bytes = struct.pack("<" + "I" * len(code), *code)
    pad = bytes(table_va - (cave_va + len(code_bytes)))
    table_bytes = struct.pack("<" + "Q" * len(table_values), *table_values)
    helper = code_bytes + pad + table_bytes
    required_order = (
        "pmode_disabled",
        "smode1_prepare",
        "sync_after_prepare_l",
        "sync_after_prepare_p",
        *timing_events,
        "sync_after_timing_l",
        "sync_after_timing_p",
        "smode1_final",
    )
    if any(a >= b for a, b in zip((events[k] for k in required_order), (events[k] for k in required_order[1:]))):
        raise PatchError("generated CRTC state transition is out of order")
    return helper, listing, table_va


def assert_cave_static_safety(
    elf: bytes,
    segment,
    va: int,
    size: int,
    *,
    section_name: str = ".rodata",
    require_executable: bool = True,
) -> None:
    """Check that a cave is a zero-filled hole in an allocated section."""
    sections = parse_sections(elf)
    section = sections.get(section_name)
    bss = sections.get(".bss")
    if section is None or bss is None:
        raise PatchError(f"expected {section_name} and .bss sections for code-cave audit")
    section_flags, section_va, _section_off, section_size = section
    _bss_flags, bss_va, _bss_off, bss_size = bss
    if (section_flags & 0x2) == 0 or (section_flags & 0x1) != 0:
        raise PatchError(f"code cave is not in a non-writable allocated {section_name} section")
    if section_name == ".text" and (section_flags & 0x4) == 0:
        raise PatchError("code cave is outside an executable .text section")
    if not (section_va <= va and va + size <= section_va + section_size):
        raise PatchError(f"code cave is outside {section_name}")
    if va < bss_va + bss_size and bss_va < va + size:
        raise PatchError("CRTC cave overlaps .bss/runtime allocation space")
    file_off = va_to_file_offset(va, size, segment, require_executable=require_executable)
    if elf[file_off : file_off + size] != bytes(size):
        raise PatchError("CRTC cave is not zero-filled in the original ELF")


def patch_word(elf: bytearray, segment, va: int, expected: int, replacement: int, reason: str):
    off = va_to_file_offset(va, 4, segment)
    before = struct.pack("<I", expected)
    after = struct.pack("<I", replacement)
    actual = bytes(elf[off : off + 4])
    if actual != before:
        raise PatchError(
            f"preimage mismatch at VA {va:#x}: got {actual.hex(' ')}, expected {before.hex(' ')} ({reason})"
        )
    elf[off : off + 4] = after
    return (va, before, after, reason)


def require_word(elf: bytes, segment, va: int, expected: int, reason: str) -> None:
    off = va_to_file_offset(va, 4, segment)
    actual = struct.unpack_from("<I", elf, off)[0]
    if actual != expected:
        raise PatchError(
            f"PMODE source preimage mismatch at VA {va:#x}: "
            f"got {actual:#010x}, expected {expected:#010x} ({reason})"
        )


def make_display_helper(
    display_value: int,
    cave_va: int,
    hook_return_va: int,
) -> bytes:
    # Build the same 40-byte helper for either the preserved trial value or a
    # phase-specific DISPLAY value. The value is assembled as four halfwords.
    halves = (
        (display_value >> 48) & 0xFFFF,
        (display_value >> 32) & 0xFFFF,
        (display_value >> 16) & 0xFFFF,
        display_value & 0xFFFF,
    )
    words = (
        encode_i(0x0F, 0, 3, halves[0]),
        encode_i(0x0D, 3, 3, halves[1]),
        encode_r(0, 3, 3, 16, 0x38),
        encode_i(0x0D, 3, 3, halves[2]),
        encode_r(0, 3, 3, 16, 0x38),
        encode_i(0x0D, 3, 3, halves[3]),
        0xFE200020, 0xFE230018,
        encode_j(cave_va + 8 * 4, hook_return_va), 0,
    )
    return struct.pack("<" + "I" * len(words), *words)


def make_dynamic_display_helper(
    cave_va: int,
    cave_size: int,
    hooks: tuple[tuple[int, int, int, int, int, int, str, str], ...],
    scale_256_rows: bool = False,
    limit_256_to_480: bool = False,
    adjust_256_dy_plus18: bool = False,
    adjust_256_dy_plus8: bool = False,
    fix_256_horizontal: bool = False,
    only_256_rows: bool = False,
) -> tuple[bytes, list[tuple[str, int]]]:
    """Build a two-entry DISPLAY helper with title-specific guarded scaling."""
    if len(hooks) != 2:
        raise PatchError("dynamic DISPLAY helper requires exactly two verified hooks")
    if limit_256_to_480 and not scale_256_rows:
        raise PatchError("256-to-480 output requires the verified DH=255 guard")
    if adjust_256_dy_plus18 and not (scale_256_rows and limit_256_to_480):
        raise PatchError("DY+18 requires the verified 6th DH=255 to 480-line path")
    if adjust_256_dy_plus8 and not (
        scale_256_rows and limit_256_to_480 and only_256_rows
    ):
        raise PatchError("DY+8 requires the guarded 256-row to 480-line path")
    if adjust_256_dy_plus8 and (adjust_256_dy_plus18 or fix_256_horizontal):
        raise PatchError("DY+8 cannot be combined with the 6th DISPLAY corrections")
    if fix_256_horizontal and not adjust_256_dy_plus18:
        raise PatchError("horizontal DISPLAY fix requires the guarded 6th DY+18 path")
    if only_256_rows and not (scale_256_rows and limit_256_to_480):
        raise PatchError("256-only DISPLAY scaling requires the guarded 480-line path")
    words: list[int] = []
    listing: list[tuple[str, int]] = []
    jump_indices = []

    def emit(text: str, word: int) -> int:
        listing.append((text, word & 0xFFFFFFFF))
        words.append(word & 0xFFFFFFFF)
        return len(words) - 1

    for entry_index, hook in enumerate(hooks):
        _hook_va, _delay_va, _hook_word, _delay_word, entry_offset, return_va, source_reg, address_reg = hook
        expected_offset = entry_index * 6 * 4
        if entry_offset != expected_offset:
            raise PatchError("dynamic DISPLAY hook entry does not match its verified cave offset")
        emit(
            f"daddu t7,{source_reg},zero",
            encode_r(0, REG[source_reg], REG["t7"], 0, 0x2D),
        )
        emit(
            f"daddu t8,{address_reg},zero",
            encode_r(0, REG[address_reg], REG["t8"], 0, 0x2D),
        )
        return_hi = (return_va >> 16) & 0xFFFF
        return_lo = return_va & 0xFFFF
        emit(f"lui t9,0x{return_hi:04x}", encode_i(0x0F, 0, REG["t9"], return_hi))
        emit(
            f"ori t9,t9,0x{return_lo:04x}",
            encode_i(0x0D, REG["t9"], REG["t9"], return_lo),
        )
        jump_indices.append(
            emit("j dynamic_display_common", 0)
        )
        emit("nop", 0)

    common_index = len(words)
    common_va = cave_va + common_index * 4
    for jump_index in jump_indices:
        pc = cave_va + jump_index * 4
        words[jump_index] = encode_j(pc, common_va)
        listing[jump_index] = (f"j {common_va:#010x}", words[jump_index])

    # DISPLAY.MAGV must be zero and DISPLAY.DH must be 239 or 223. The
    # selected 256-row titles also accept DH=255. The shared scale path computes
    # DH' = 2*DH+1. For DH=255 only, add bit 5 to its XOR mask so DH'=479;
    # the masks for DH=223/239 already have bit 5 set. MAGV becomes one.
    # Optional DY correction is separately guarded by original DH=255. A
    # title can also restrict scaling to that input alone, bypassing 223/239.
    # All other DISPLAY fields and unrecognized modes pass through unchanged.
    emit("dsrl t0,t7,27", encode_r(0, REG["t7"], REG["t0"], 27, 0x3A))
    emit("andi t0,t0,3", encode_i(0x0C, REG["t0"], REG["t0"], 3))
    magv_branch = emit("bne t0,zero,store_display", 0)
    emit("nop", 0)
    emit("dsrl32 t0,t7,12", encode_r(0, REG["t7"], REG["t0"], 12, 0x3E))
    emit("andi t0,t0,0x07ff", encode_i(0x0C, REG["t0"], REG["t0"], 0x07FF))
    dh239_branch = None
    dh223_branch = None
    dh255_branch = None
    if only_256_rows:
        # The title hook is scoped to its verified 640x256 mode. Check only
        # original DH=255; all other row counts retain the full value.
        emit("addiu t1,zero,255", encode_i(0x09, 0, REG["t1"], 255))
        dh255_branch = emit("bne t0,t1,store_display", 0)
        emit("nop", 0)
    else:
        emit("addiu t1,zero,239", encode_i(0x09, 0, REG["t1"], 239))
        dh239_branch = emit("beq t0,t1,scale_display", 0)
        if scale_256_rows:
            # Both branch delay slots only load t1. The scale path overwrites t1
            # before using it, so these loads are safe whether a branch is taken.
            emit("addiu t1,zero,223 ; delay slot", encode_i(0x09, 0, REG["t1"], 223))
            dh223_branch = emit("beq t0,t1,scale_display", 0)
            emit("addiu t1,zero,255 ; delay slot", encode_i(0x09, 0, REG["t1"], 255))
            dh255_branch = emit("bne t0,t1,store_display", 0)
            emit("nop", 0)
        else:
            emit("nop", 0)
            emit("addiu t1,zero,223", encode_i(0x09, 0, REG["t1"], 223))
            dh223_branch = emit("bne t0,t1,store_display", 0)
            emit("nop", 0)
    scale_index = len(words)
    if adjust_256_dy_plus18:
        # Save DY for the guarded correction. Unrecognized modes branch to the
        # original store before reaching this point, so their temporaries stay
        # untouched. Scaled non-255 modes restore the legacy t2 scratch value.
        emit("dsrl t2,t7,12", encode_r(0, REG["t7"], REG["t2"], 12, 0x3A))
    if only_256_rows:
        # The guard above proves original DH=255, so its exact 255->479 XOR
        # mask is 0x120. This saves three instructions within the audited cave.
        emit("addiu t1,zero,0x120", encode_i(0x09, 0, REG["t1"], 0x120))
    else:
        emit("dsll t1,t0,1", encode_r(0, REG["t0"], REG["t1"], 1, 0x38))
        emit("ori t1,t1,1", encode_i(0x0D, REG["t1"], REG["t1"], 1))
        emit("xor t1,t1,t0", encode_r(REG["t1"], REG["t0"], REG["t1"], 0, 0x26))
    if limit_256_to_480 and not only_256_rows:
        # XOR masks: 223->447 = 0x160, 239->479 = 0x130, 255->511 = 0x100.
        # OR 0x20 preserves the first two and makes 255->479 mask 0x120.
        emit("ori t1,t1,0x20", encode_i(0x0D, REG["t1"], REG["t1"], 0x20))
    emit("dsll32 t1,t1,12", encode_r(0, REG["t1"], REG["t1"], 12, 0x3C))
    emit("xor t7,t7,t1", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x26))
    if adjust_256_dy_plus18:
        # t2 holds the original 11-bit DY. Reuse t1 after the DH mask is
        # applied to set MAGV, then add 18 modulo 2048 to DY only for DH=255.
        emit("lui t1,0x0800", encode_i(0x0F, 0, REG["t1"], 0x0800))
        emit("or t7,t7,t1", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x25))
        emit("xori t0,t0,255", encode_i(0x0E, REG["t0"], REG["t0"], 255))
        dy_gate_branch = emit("bne t0,zero,restore_scaled_t2", 0)
        emit("xori t0,t0,255 ; delay slot restores source DH", encode_i(0x0E, REG["t0"], REG["t0"], 255))
        emit("andi t2,t2,0x07ff", encode_i(0x0C, REG["t2"], REG["t2"], 0x07FF))
        emit("addiu t1,t2,18", encode_i(0x09, REG["t2"], REG["t1"], 18))
        emit("andi t1,t1,0x07ff", encode_i(0x0C, REG["t1"], REG["t1"], 0x07FF))
        emit("xor t1,t1,t2", encode_r(REG["t1"], REG["t2"], REG["t1"], 0, 0x26))
        emit("dsll t1,t1,12", encode_r(0, REG["t1"], REG["t1"], 12, 0x38))
        emit("xor t7,t7,t1", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x26))
        if fix_256_horizontal:
            # This path is reached only for original MAGV=0,DH=255. Extract
            # each old horizontal field, XOR it with its replacement, then
            # shift the difference back into place. Other DISPLAY bits,
            # including the corrected DY/MAGV/DH, are left untouched.
            emit("andi t1,t7,0x0fff ; old DX", encode_i(0x0C, REG["t7"], REG["t1"], 0x0FFF))
            emit("xori t1,t1,312", encode_i(0x0E, REG["t1"], REG["t1"], 312))
            emit("xor t7,t7,t1 ; replace DX", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x26))
            emit("dsrl t1,t7,23 ; old MAGH", encode_r(0, REG["t7"], REG["t1"], 23, 0x3A))
            emit("andi t1,t1,0x000f", encode_i(0x0C, REG["t1"], REG["t1"], 0x000F))
            emit("xori t1,t1,1", encode_i(0x0E, REG["t1"], REG["t1"], 1))
            emit("dsll t1,t1,23", encode_r(0, REG["t1"], REG["t1"], 23, 0x38))
            emit("xor t7,t7,t1 ; replace MAGH", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x26))
            emit("dsrl32 t1,t7,0 ; old DW", encode_r(0, REG["t7"], REG["t1"], 0, 0x3E))
            emit("andi t1,t1,0x0fff", encode_i(0x0C, REG["t1"], REG["t1"], 0x0FFF))
            emit("xori t1,t1,1279", encode_i(0x0E, REG["t1"], REG["t1"], 1279))
            emit("dsll32 t1,t1,0", encode_r(0, REG["t1"], REG["t1"], 0, 0x3C))
            emit("xor t7,t7,t1 ; replace DW", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x26))
        dy_restore_index = len(words)
        emit("lui t2,0x0800 ; restore legacy scratch value", encode_i(0x0F, 0, REG["t2"], 0x0800))
    elif adjust_256_dy_plus8:
        # This path is reachable only for original MAGV=0,DH=255. Form the
        # wrapped DY difference and combine it with the MAGV bit before XORing
        # into DISPLAY, preserving every other field and the legacy t2 result.
        emit("dsrl t2,t7,12 ; source DY", encode_r(0, REG["t7"], REG["t2"], 12, 0x3A))
        emit("andi t2,t2,0x07ff", encode_i(0x0C, REG["t2"], REG["t2"], 0x07FF))
        emit("addiu t1,t2,8", encode_i(0x09, REG["t2"], REG["t1"], 8))
        emit("andi t1,t1,0x07ff", encode_i(0x0C, REG["t1"], REG["t1"], 0x07FF))
        emit("xor t1,t1,t2", encode_r(REG["t1"], REG["t2"], REG["t1"], 0, 0x26))
        emit("dsll t1,t1,12", encode_r(0, REG["t1"], REG["t1"], 12, 0x38))
        emit("lui t2,0x0800", encode_i(0x0F, 0, REG["t2"], 0x0800))
        emit("or t1,t1,t2", encode_r(REG["t1"], REG["t2"], REG["t1"], 0, 0x25))
        emit("xor t7,t7,t1", encode_r(REG["t7"], REG["t1"], REG["t7"], 0, 0x26))
    else:
        emit("lui t2,0x0800", encode_i(0x0F, 0, REG["t2"], 0x0800))
        emit("or t7,t7,t2", encode_r(REG["t7"], REG["t2"], REG["t7"], 0, 0x25))
    store_index = len(words)
    emit("sd t7,0(t8)", encode_i(0x3F, REG["t8"], REG["t7"], 0))
    emit("jr t9", encode_r(REG["t9"], 0, 0, 0, 0x08))
    emit("nop", 0)

    branch_targets = [(magv_branch, store_index, 0x05, REG["zero"])]
    if dh239_branch is not None:
        branch_targets.append((dh239_branch, scale_index, 0x04, REG["t1"]))
    if dh223_branch is not None:
        branch_targets.append((
            dh223_branch,
            scale_index if scale_256_rows else store_index,
            0x04 if scale_256_rows else 0x05,
            REG["t1"],
        ))
    if dh255_branch is not None:
        branch_targets.append((dh255_branch, store_index, 0x05, REG["t1"]))
    for branch_index, target_index, op, rt in branch_targets:
        relative = target_index - (branch_index + 1)
        rs = REG["t0"]
        words[branch_index] = encode_i(op, rs, rt, relative)
        listing[branch_index] = (
            f"{'beq' if op == 0x04 else 'bne'} t0,{('t1' if rt == REG['t1'] else 'zero')},"
            f"{('scale_display' if target_index == scale_index else 'store_display')}",
            words[branch_index],
        )
    if adjust_256_dy_plus18:
        relative = dy_restore_index - (dy_gate_branch + 1)
        words[dy_gate_branch] = encode_i(0x05, REG["t0"], REG["zero"], relative)
        listing[dy_gate_branch] = (
            f"bne t0,zero,{cave_va + dy_restore_index * 4:#010x}",
            words[dy_gate_branch],
        )

    words.extend([0] * (cave_size // 4 - len(words)))
    listing.extend([("nop ; unused verified cave padding", 0)] * (cave_size // 4 - len(listing)))
    if cave_size % 4 or len(words) * 4 != cave_size:
        raise PatchError("dynamic DISPLAY helper exceeds its verified cave")
    return struct.pack("<" + "I" * len(words), *words), listing


def decode_display_value(display_value: int) -> tuple[int, int, int, int, int, int]:
    """Return GS DISPLAY fields in DX, DY, MAGH, MAGV, DW, DH order."""
    return (
        display_value & 0xFFF,
        (display_value >> 12) & 0x7FF,
        (display_value >> 23) & 0xF,
        (display_value >> 27) & 0x3,
        (display_value >> 32) & 0xFFF,
        (display_value >> 44) & 0x7FF,
    )


def assert_title_cave_is_unused(
    elf: bytes,
    segment,
    title_config: dict,
    va: int,
    size: int,
    *,
    require_executable: bool = True,
    scan_pointer_range: bool = True,
) -> None:
    """Audit a title-specific zero cave against code and aligned ELF pointers."""
    file_off = va_to_file_offset(
        va, size, segment, require_executable=require_executable
    )
    if elf[file_off : file_off + size] != bytes(size):
        raise PatchError(f"code cave {va:#x}+{size:#x} is not zero-filled")

    if title_config.get("stripped"):
        code_regions = []
        for p_off, p_va, p_filesz, _p_memsz, p_flags in segment:
            if p_filesz and p_flags & 1:
                if p_filesz % 4:
                    raise PatchError("stripped executable PT_LOAD is not word-aligned")
                code_regions.append((p_va, elf[p_off : p_off + p_filesz]))
        if not code_regions:
            raise PatchError("stripped title has no file-backed executable PT_LOAD")
    else:
        text_va, text_off, text_size = title_config["text"]
        sections = parse_sections(elf)
        text_section = sections.get(".text")
        if text_section != (0x6, text_va, text_off, text_size):
            raise PatchError(f"unexpected {title_config['title']} .text section: {text_section!r}")
        text = elf[text_off : text_off + text_size]
        if len(text) != text_size or text_size % 4:
            raise PatchError("invalid title .text bounds for code-cave audit")
        code_regions = [(text_va, text)]

    for text_va, text in code_regions:
        words = struct.unpack("<" + "I" * (len(text) // 4), text)
        for index, word in enumerate(words):
            pc = text_va + index * 4
            op = word >> 26
            if op in (2, 3):
                target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
                if va <= target < va + size:
                    raise PatchError(f"existing jump enters code cave from {pc:#x}")
            elif op in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
                immediate = word & 0xFFFF
                if immediate & 0x8000:
                    immediate -= 0x10000
                target = pc + 4 + (immediate << 2)
                if va <= target < va + size:
                    raise PatchError(f"existing branch enters code cave from {pc:#x}")

            if op != 0x0F:  # LUI
                continue
            reg = (word >> 16) & 31
            high = word & 0xFFFF
            for j in range(index + 1, min(index + 12, len(words))):
                q = words[j]
                qop, rs, rt, imm = q >> 26, (q >> 21) & 31, (q >> 16) & 31, q & 0xFFFF
                if rs != reg:
                    continue
                if qop in (0x08, 0x09, 0x18, 0x19):
                    signed = imm - 0x10000 if imm & 0x8000 else imm
                    target = ((high << 16) + signed) & 0xFFFFFFFF
                    if va <= target < va + size:
                        raise PatchError(
                            f"existing LUI-derived address reference to code cave at {target:#x}"
                        )
                elif qop == 0x0D:
                    target = (high << 16) | imm
                    if va <= target < va + size:
                        raise PatchError(
                            f"existing LUI-derived address reference to code cave at {target:#x}"
                        )
                elif qop == 0x0C:
                    target = (high << 16) & imm
                    if va <= target < va + size:
                        raise PatchError(
                            f"existing LUI-derived address reference to code cave at {target:#x}"
                        )
                elif qop == 0x0E:
                    target = (high << 16) ^ imm
                    if va <= target < va + size:
                        raise PatchError(
                            f"existing LUI-derived address reference to code cave at {target:#x}"
                        )

                # Detect direct memory operands built from the LUI base even if no
                # ADDIU/ORI materializes the complete address in that register.
                if qop in (0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x28, 0x29, 0x2B, 0x2C, 0x2D, 0x37, 0x3F, 0x1E, 0x1F):
                    signed = imm - 0x10000 if imm & 0x8000 else imm
                    target = ((high << 16) + signed) & 0xFFFFFFFF
                    if va <= target < va + size:
                        raise PatchError(f"existing LUI memory reference to code cave at {target:#x}")

    # Catch static data pointers as well as code references. Restricting the
    # target to the exact payload range avoids rejecting unrelated zero padding.
    for pos in range(0, len(elf) - 3, 4):
        if file_off <= pos < file_off + size:
            continue
        target = struct.unpack_from("<I", elf, pos)[0]
        points_into_cave = (
            va <= target < va + size if scan_pointer_range else target == va
        )
        if points_into_cave:
            raise PatchError(f"aligned ELF pointer at file offset {pos:#x} enters code cave")


def make_patched_elf_for_title(
    elf: bytes, product_code: str, profile_name: str = "v1.0"
):
    """Build any supported title from the same verified patch plan."""
    if profile_name not in PATCH_PROFILES:
        raise PatchError(f"unknown patch profile: {profile_name}")
    if product_code not in TITLE_CONFIGS:
        raise PatchError(f"no title configuration for {product_code}")
    config = TITLE_CONFIGS[product_code]
    profile = PATCH_PROFILES[profile_name]
    segment = parse_title_load_segment(elf, product_code)
    if sha256_bytes(elf) != config["elf_sha256"]:
        raise PatchError(f"unsupported or modified {config['title']} ELF")
    for va, expected, reason in config["pmode_checks"]:
        require_word(elf, segment, va, expected, reason)

    dynamic_display = config.get("display_mode") == "dynamic_240_or_224_rows"
    if dynamic_display:
        display_helper, _display_listing = make_dynamic_display_helper(
            config["display_cave_va"],
            config["display_cave_size"],
            config["display_hooks"],
            scale_256_rows=config.get("display_scale_256_rows", False),
            limit_256_to_480=config.get("display_256_to_480", False),
            adjust_256_dy_plus18=config.get("display_256_dy_plus18", False),
            adjust_256_dy_plus8=config.get("display_256_dy_plus8", False),
            fix_256_horizontal=config.get("display_256_horizontal_fix", False),
            only_256_rows=config.get("display_only_256_rows", False),
        )
    else:
        display_helper = make_display_helper(
            config.get("display_value", profile["display_value"]),
            config["display_cave_va"],
            config["display_hook_return_va"],
        )
    crtc_helper, listing, table_va = build_crtc_helper(
        config.get("timing_values", profile["timing_values"]),
        config["crtc_cave_va"],
    )
    if len(display_helper) != config.get("display_helper_size", config["display_cave_size"]):
        raise PatchError(f"unexpected {config['title']} DISPLAY helper size")
    if len(crtc_helper) > config["crtc_cave_size"]:
        raise PatchError(f"{config['title']} CRTC helper exceeds its verified cave")
    assert_title_cave_is_unused(
        elf,
        segment,
        config,
        config["display_cave_va"],
        config["display_cave_size"],
        require_executable=config.get("display_cave_executable", True),
        scan_pointer_range=config.get("display_scan_pointer_range", True),
    )
    assert_title_cave_is_unused(
        elf,
        segment,
        config,
        config["crtc_cave_va"],
        config["crtc_cave_size"],
        require_executable=config.get("crtc_cave_executable", True),
    )
    if config.get("static_section_safety", True):
        assert_cave_static_safety(
            elf,
            segment,
            config["display_cave_va"],
            config["display_cave_size"],
            section_name=config.get("display_cave_section", ".rodata"),
            require_executable=config.get("display_cave_executable", True),
        )
        assert_cave_static_safety(
            elf,
            segment,
            config["crtc_cave_va"],
            config["crtc_cave_size"],
            section_name=config.get("crtc_cave_section", ".rodata"),
            require_executable=config.get("crtc_cave_executable", True),
        )

    patched = bytearray(elf)
    rows = []
    for patch in config["mode_patches"]:
        rows.append(patch_word(patched, segment, *patch))

    # One 7th Style static branch target lands in the zero-filled guard word
    # immediately before the CRTC cave. Keep that pre-existing path from
    # falling through into the injected helper; the jump delay slot remains NOP.
    if "crtc_cave_guard" in config:
        guard_va, guard_expected, guard_delay_va, guard_delay_expected = config["crtc_cave_guard"]
        guard_source_va, guard_source_expected = config["crtc_cave_guard_source"]
        require_word(
            elf,
            segment,
            guard_source_va,
            guard_source_expected,
            "pre-existing branch to the zero-run guard word",
        )
        source_word = struct.unpack_from(
            "<I", elf, va_to_file_offset(guard_source_va, 4, segment)
        )[0]
        immediate = source_word & 0xFFFF
        if immediate & 0x8000:
            immediate -= 0x10000
        branch_target = guard_source_va + 4 + (immediate << 2)
        if source_word >> 26 not in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17) or branch_target != guard_va:
            raise PatchError(f"{config['title']} CRTC guard branch no longer targets the audited NOP")
        guard_delay_off = va_to_file_offset(guard_delay_va, 4, segment)
        if struct.unpack_from("<I", elf, guard_delay_off)[0] != guard_delay_expected:
            raise PatchError(f"{config['title']} CRTC guard delay slot changed")
        guard_target = config["crtc_cave_va"] + len(crtc_helper)
        if not (
            config["crtc_cave_va"] + len(crtc_helper)
            <= guard_target
            < config["crtc_cave_va"] + config["crtc_cave_size"]
        ):
            raise PatchError(f"{config['title']} CRTC guard target is outside the zero-filled cave tail")
        rows.append(
            patch_word(
                patched,
                segment,
                guard_va,
                guard_expected,
                encode_j(guard_va, guard_target),
                f"{config['title']} skip helper from pre-existing zero-run branch target",
            )
        )

    wrapper_va = config["setgscrt_wrapper_va"]
    reset_tails = (
        config["resetgraph_tails"]
        if "resetgraph_tails" in config
        else ((config["resetgraph_tail_va"], config["resetgraph_delay_va"]),)
    )
    for reset_va, reset_delay_va in reset_tails:
        rows.append(
            patch_word(
                patched,
                segment,
                reset_va,
                encode_j(reset_va, wrapper_va),
                encode_j(reset_va, config["crtc_cave_va"]),
                f"{config['title']} ResetGraph tail to BIOS-aware CRTC helper",
            )
        )
        reset_delay_off = va_to_file_offset(reset_delay_va, 4, segment)
        expected_delay = config.get("resetgraph_delay_word", 0x27BD0050)
        if struct.unpack_from("<I", elf, reset_delay_off)[0] != expected_delay:
            raise PatchError(f"{config['title']} ResetGraph stack-restoring delay slot changed")

    if dynamic_display:
        for hook in config["display_hooks"]:
            hook_va, delay_va, expected_hook, expected_delay, entry_offset, _return_va, _source, _address = hook
            delay_off = va_to_file_offset(delay_va, 4, segment)
            if struct.unpack_from("<I", elf, delay_off)[0] != expected_delay:
                raise PatchError(f"{config['title']} DISPLAY hook delay instruction changed")
            rows.append(
                patch_word(
                    patched,
                    segment,
                    hook_va,
                    expected_hook,
                    encode_j(hook_va, config["display_cave_va"] + entry_offset),
                    f"{config['title']} dynamic DISPLAY helper hook",
                )
            )
    else:
        display_va = config["display_hook_va"]
        display_delay_off = va_to_file_offset(config["display_hook_delay_va"], 4, segment)
        if struct.unpack_from("<I", elf, display_delay_off)[0] != 0xDFBF0060:
            raise PatchError(f"{config['title']} DISPLAY hook delay slot changed")
        rows.append(
            patch_word(
                patched,
                segment,
                display_va,
                0xFE200020,
                encode_j(display_va, config["display_cave_va"]),
                f"{config['title']} DISPLAY helper hook",
            )
        )

    wrapper_off = va_to_file_offset(wrapper_va, 16, segment)
    expected_wrapper = (0x24030002, 0x0000000C, 0x03E00008, 0x00000000)
    if struct.unpack_from("<4I", elf, wrapper_off) != expected_wrapper:
        raise PatchError(f"{config['title']} SetGsCrt syscall wrapper preimage changed")

    # The generated helper writes PMODE=0 to blank the circuits; it never reads
    # PMODE back. IIDX later restores its own value from the display environment.
    for offset in range(0, len(listing) * 4, 4):
        word = struct.unpack_from("<I", crtc_helper, offset)[0]
        if (word >> 26) == 0x37 and ((word >> 21) & 31) == REG["t0"] and (word & 0xFFFF) == GS_PMODE_OFFSET:
            raise PatchError(f"generated {config['title']} CRTC helper unexpectedly reads GS PMODE")

    display_off = title_patch_va_to_file_offset(
        config["display_cave_va"], len(display_helper), segment, config
    )
    patched[display_off : display_off + len(display_helper)] = display_helper
    crtc_off = title_patch_va_to_file_offset(
        config["crtc_cave_va"], len(crtc_helper), segment, config
    )
    patched[crtc_off : crtc_off + len(crtc_helper)] = crtc_helper
    rows.extend(
        (
            (config["display_cave_va"], bytes(len(display_helper)), display_helper, f"{config['title']} DISPLAY helper"),
            (config["crtc_cave_va"], bytes(len(crtc_helper)), crtc_helper, f"{config['title']} BIOS-aware CRTC helper and value table"),
        )
    )
    return bytes(patched), rows, listing, table_va


def make_patched_elf_profiled_title(
    elf: bytes, product_code: str, profile_name: str = "v1.0"
):
    """Keep the API used by existing IIDX 8th diagnostic scripts."""
    return make_patched_elf_for_title(elf, product_code, profile_name)


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result = []
    for start, length in sorted(ranges):
        if length <= 0:
            raise PatchError("empty patch range")
        end = start + length
        if result and start < result[-1][1]:
            raise PatchError("overlapping ISO patch ranges")
        result.append((start, end))
    return result


def compare_outside_ranges(source: Path, output: Path, ranges: list[tuple[int, int]]) -> tuple[str, str]:
    merged = merge_ranges(ranges)
    source_hash = hashlib.sha256()
    output_hash = hashlib.sha256()
    with source.open("rb") as left, output.open("rb") as right:
        offset = 0
        while True:
            a = left.read(8 * 1024 * 1024)
            b = right.read(8 * 1024 * 1024)
            if len(a) != len(b):
                raise PatchError("output size differs from source")
            if not a:
                break
            source_hash.update(a)
            output_hash.update(b)
            chunk_end = offset + len(a)
            cursor = offset
            for start, end in merged:
                if end <= cursor or start >= chunk_end:
                    continue
                allowed_start = max(start, cursor)
                allowed_end = min(end, chunk_end)
                if a[cursor - offset : allowed_start - offset] != b[cursor - offset : allowed_start - offset]:
                    raise PatchError(f"unexpected ISO difference near {cursor:#x}")
                cursor = allowed_end
            if a[cursor - offset :] != b[cursor - offset :]:
                raise PatchError(f"unexpected ISO difference near {cursor:#x}")
            offset = chunk_end
    return source_hash.hexdigest().upper(), output_hash.hexdigest().upper()


def check_output_space(output_dir: Path, output_size: int) -> int:
    """Require space for a full ISO copy plus filesystem/write headroom."""
    if output_size <= 0:
        raise PatchError(f"invalid output size for space preflight: {output_size}")
    required = output_size + max(MIN_OUTPUT_SPACE_MARGIN, output_size // 100)
    try:
        available = shutil.disk_usage(output_dir).free
    except OSError as exc:
        raise PatchError(f"cannot determine free space for output directory: {exc}") from exc
    if available < required:
        raise PatchError(
            "insufficient free disk space for a safe ISO output: "
            f"need at least {required} bytes including headroom, have {available}"
        )
    return required


def build(
    source: Path,
    output: Path,
    profile_name: str = "v1.0",
) -> tuple[str, str, str, int, list[tuple[str, int]], str, int]:
    source = source.resolve()
    output = output.resolve()
    partial = output.with_name(output.name + ".partial")
    if source == output or source == partial:
        raise PatchError("source and output paths must be different")
    if output.exists() or output.is_symlink():
        raise PatchError(f"output already exists; refusing to overwrite: {output}")
    if partial.exists() or partial.is_symlink():
        raise PatchError(f"partial output already exists; refusing to overwrite: {partial}")
    if not source.is_file():
        raise PatchError(f"source ISO not found: {source}")
    if not output.parent.is_dir():
        raise PatchError(f"output directory does not exist: {output.parent}")
    check_output_space(output.parent, source.stat().st_size)

    elf_iso_offset, elf_size, original_elf, product_code = locate_boot_elf(source)
    segment = parse_title_load_segment(original_elf, product_code)
    patched_elf, patch_rows, listing, table_va = make_patched_elf_for_title(
        original_elf, product_code, profile_name
    )
    patched_elf_hash = sha256_bytes(patched_elf)
    title_config = TITLE_CONFIGS[product_code]
    expected_patched_hash = title_config["patched_elf_sha256"]
    if expected_patched_hash is not None and patched_elf_hash != expected_patched_hash:
        raise PatchError(f"generated patched ELF hash is unexpected: {patched_elf_hash}")

    iso_ranges = []
    for va, _before, _after, _reason in patch_rows:
        # Every row's length is either one instruction or the exact cave payload.
        length = len(_after)
        elf_off = title_patch_va_to_file_offset(va, length, segment, title_config)
        iso_ranges.append((elf_iso_offset + elf_off, length))
    merge_ranges(iso_ranges)

    published = False
    try:
        source_hash_before = sha256_file(source)
        copied = hashlib.sha256()
        with source.open("rb") as src, partial.open("xb") as dst:
            while chunk := src.read(8 * 1024 * 1024):
                dst.write(chunk)
                copied.update(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        if copied.hexdigest().upper() != source_hash_before:
            raise PatchError("source changed during copy")

        with partial.open("r+b") as stream:
            stream.seek(elf_iso_offset)
            stream.write(patched_elf)
            stream.flush()
            os.fsync(stream.fileno())

        with partial.open("rb") as stream:
            written_elf = read_at(stream, elf_iso_offset, elf_size)
        if written_elf != patched_elf:
            raise PatchError("patched boot ELF failed byte verification")
        for va, _before, after, _reason in patch_rows:
            elf_off = title_patch_va_to_file_offset(
                va, len(after), segment, title_config
            )
            if written_elf[elf_off : elf_off + len(after)] != after:
                raise PatchError(f"patched bytes failed verification at VA {va:#x}")

        source_hash_after, output_hash = compare_outside_ranges(source, partial, iso_ranges)
        if source_hash_after != source_hash_before:
            raise PatchError(f"source ISO changed while patching: {source_hash_after}")
        if partial.stat().st_size != source.stat().st_size:
            raise PatchError("output size differs from original ISO")

        os.rename(partial, output)
        published = True
        if sha256_file(output) != output_hash:
            raise PatchError("final ISO SHA-256 changed after publication")
        out_iso_offset, out_elf_size, out_elf, output_product_code = locate_boot_elf(
            output, verify_original_elf=False
        )
        if (
            output_product_code != product_code
            or out_iso_offset != elf_iso_offset
            or out_elf_size != elf_size
            or out_elf != patched_elf
        ):
            raise PatchError("final ISO BOOT2 verification failed")
        if expected_patched_hash is not None and sha256_bytes(out_elf) != expected_patched_hash:
            raise PatchError("final patched boot ELF hash verification failed")
        crtc_payloads = [
            after for va, _before, after, _reason in patch_rows
            if va == title_config["crtc_cave_va"]
        ]
        if len(crtc_payloads) != 1:
            raise PatchError("generated patch is missing its unique CRTC helper")
        return (
            source_hash_after,
            output_hash,
            sha256_bytes(out_elf),
            len(crtc_payloads[0]),
            listing,
            product_code,
            table_va,
        )
    except Exception:
        partial.unlink(missing_ok=True)
        if published:
            output.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="your own supported IIDX PS2 ISO dump")
    parser.add_argument("--output", type=Path, help="new output ISO path; refuses to overwrite existing files")
    args = parser.parse_args()
    try:
        output_arg = args.output or args.source.with_name(args.source.stem + "_480p_v1.0.iso")
        source_hash, output_hash, elf_hash, helper_size, _listing, product_code, table_va = build(
            args.source, output_arg, "v1.0"
        )
        output = output_arg.resolve()
        title_config = TITLE_CONFIGS[product_code]
        profile = PATCH_PROFILES["v1.0"]
        timing_values = title_config.get("timing_values", profile["timing_values"])
        cave_va = title_config["crtc_cave_va"]
        print(f"TITLE={title_config['title']}")
        print(f"STATE={title_config['state']}")
        print(f"SOURCE={args.source.resolve()}")
        print(f"SOURCE_SHA256={source_hash}")
        print(f"OUTPUT={output}")
        print(f"OUTPUT_SIZE={output.stat().st_size}")
        print(f"OUTPUT_SHA256={output_hash}")
        print(f"PATCHED_ELF_SHA256={elf_hash}")
        print(f"CRTC_HELPER_VA={cave_va:#010x}")
        print(f"CRTC_HELPER_SIZE={helper_size}")
        print(f"CRTC_TABLE_VA={table_va:#010x}")
        if title_config.get("display_mode") == "dynamic_240_or_224_rows":
            if title_config.get("display_only_256_rows", False):
                print("DISPLAY_MODE=guarded: DH 255->479 when MAGV=0; all other modes pass through")
            else:
                print("DISPLAY_MODE=guarded: DH 255->479, 239->479, or 223->447 when MAGV=0; other values pass through")
            if title_config.get("display_256_dy_plus18", False):
                print("DISPLAY_DY=add 18 modulo 2048 only for input MAGV=0,DH=255")
            if title_config.get("display_256_dy_plus8", False):
                print("DISPLAY_DY=add 8 modulo 2048 only for input MAGV=0,DH=255")
            if title_config.get("display_256_horizontal_fix", False):
                print("DISPLAY_HORIZONTAL=DX:312,MAGH:1,DW:1279 only for input MAGV=0,DH=255")
            print("DISPLAY_VALUE=read from the live IIDX display environment")
        else:
            display_value = title_config.get("display_value", profile["display_value"])
            print(f"DISPLAY_VALUE={display_value:#018x}")
            dx, dy, magh, magv, dw, dh = decode_display_value(display_value)
            print(
                f"DISPLAY_FIELDS=DX:{dx},DY:{dy},MAGH:{magh},MAGV:{magv},DW:{dw},DH:{dh},"
                f"source_rows:{(dh + 1) // (magv + 1)}"
            )
        print(f"SYNCV={timing_values[-1]:#018x}")
        print("BIOS_OSD_COLOR=preserved at runtime; no fixed RGB/component selection")
        print("PMODE=runtime game display-env restore; no GS PMODE readback")
        print("HARDWARE_VALIDATION=not performed by this tool")
        print("INPUT=ISO9660 SYSTEM.CNF BOOT2 extent discovered dynamically; full-ISO hash is informational")
        print("VERIFIED=ELF allowlist, MIPS preimages, code caves, patched ELF hash, and non-patch ISO bytes")
        return 0
    except (PatchError, OSError, struct.error, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
