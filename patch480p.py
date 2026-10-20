#!/usr/bin/env python3
"""Patch a supported IIDX 3rd Style ISO to the verified 480p v1.0 profile.

Only the exact allowlisted BOOT2 ELF is accepted. The ISO and boot ELF extents
are read from ISO9660/SYSTEM.CNF; the input image itself is never modified.
Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import sys
from pathlib import Path


SECTOR_SIZE = 2048
SUPPORTED_PRODUCT_CODE = "SLPM_650.06"
SUPPORTED_ELF_SHA256 = "CD2EE5A1C50C46808927EF32A7FE8F5791AE66399DA029A75D5095CA70499321"
PATCHED_ELF_SHA256 = "12CC9C5F6DA5AB7581BFD5B5C9F185BAB80EC2C649303CE6D4ACDB825DA83292"
# Reject known development outputs explicitly instead of treating them as a
# supported original revision. Other modified ELFs are rejected by the allowlist.
ALREADY_PATCHED_ELF_SHA256S = {
    "CFBFC4BA81CEF34EA021100FCD42F34F224AE95AD7B71D5423F59C2612DABF8A",
    "1300A2CF006F401358F5115769F8E6889805AC5D79EE4993B620AED1E3ADD449",
    PATCHED_ELF_SHA256,
    "B15A3794774CDBF4F50051CA1FC8BB630D71FE815AE5B7B70A8F19709CF49362",
}
MAX_BOOT_ELF_SIZE = 128 * 1024 * 1024  # Defensive parser limit, not a revision check.

TEXT_VA = 0x00100000
TEXT_SIZE = 0x000765EC
LOAD_FILE_OFFSET = 0x1000
LOAD_VA = 0x00100000
LOAD_FILE_SIZE = 0x00089E249
LOAD_FLAGS = 0x7  # PT_LOAD is readable, writable, and executable.

# Existing 240p-to-480p DISPLAY path, independently verified in the earlier
# trial. Keep this part unchanged in this color/CRTC correction.
DISPLAY_CAVE_VA = 0x00171808
DISPLAY_CAVE_SIZE = 0x3A
DISPLAY_HOOK_VA = 0x001581C0
DISPLAY_HOOK_DELAY_VA = 0x001581C4
DISPLAY_HOOK_RETURN_VA = 0x001581C8
DISPLAY_VALUE = 0x001BF4FF08833138
# Phase 4 uses the HOW TO PLAY dump's 240-row SCISSOR window: 2x vertical
# magnification produces 480 output lines. The helper's DY=43 compensates the
# previously observed -8 line change, targeting GS DY=35.
PHASE4_DISPLAY_VALUE = 0x001DF4FF0882B138
# First Phase 4 diagnostic: show all 256 source rows at 1x vertical scale and
# center them in the 480-line active region. The observed helper-to-GS DY delta
# is -8: GSKit's DTV480P StartY 35 + (480-256)/2 = 147, so encode DY=155.
# MAGV=0 and DH=255 preserve all 256 source rows; horizontal output remains 2x.
PHASE4_FULL256_DISPLAY_VALUE = 0x000FF4FF0089B138

# New helper is placed in a zero-filled .rodata hole in the PT_LOAD segment.
# Static references/stores and segment/section bounds are checked separately.
CRTC_CAVE_VA = 0x002A3980
CRTC_CAVE_SIZE = 0x118

RESETGRAPH_TAIL_VA = 0x00157378
RESETGRAPH_DELAY_VA = 0x0015737C
SETGSCRT_WRAPPER_VA = 0x00171860

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

CRTC_TIMING_VALUES = (
    0x0000000000000002,  # SMODE2
    0x0000000000000004,  # SRFSH
    0x000402DA20034020,  # SYNCH1
    0x000000000019D272,  # SYNCH2
    0x00C78C0001E00006,  # SYNCV: standard DTV-480P, 525 total lines
)
# Timing-only Phase 4 candidate: hold the tested 240-row / 2x DISPLAY setup
# and all other CRTC values fixed while advancing SYNCV.VDP by one. This is
# the 526-line / ~59.83 Hz hardware hypothesis; it is not asserted as verified.
PHASE4_VDP484_TIMING_VALUES = (
    *CRTC_TIMING_VALUES[:-1],
    0x00C7900001E00006,  # SYNCV: VDP 483 -> 484; hypothesized 526 total lines
)
CRTC_REGISTER_OFFSETS = (
    GS_SMODE2_OFFSET,
    GS_SRFSH_OFFSET,
    GS_SYNCH1_OFFSET,
    GS_SYNCH2_OFFSET,
    GS_SYNCV_OFFSET,
)

PATCH_PROFILES = {
    "v1.0": {
        "display_value": PHASE4_DISPLAY_VALUE,
        "timing_values": PHASE4_VDP484_TIMING_VALUES,
        "state": "PATCHED_IIDX03_480P_V1_0",
        "description": "verified full-240-row 480p output with SYNCV.VDP=484",
    },
}

SYSCALL_SETGSCRT = 0x02
SYSCALL_GETOSDCONFIGPARAM = 0x4B
SYSCALL_SETGSVPARAM = 0x4F
SYNC_L_WORD = 0x0000000F  # SPECIAL, stype=0, funct=SYNC
SYNC_P_WORD = 0x0000040F  # SPECIAL, stype=16, funct=SYNC

REG = {
    "zero": 0, "v0": 2, "v1": 3,
    "a0": 4, "a1": 5, "a2": 6,
    "t0": 8, "t1": 9, "t2": 10, "t3": 11, "t4": 12, "t9": 25,
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


def locate_boot_elf(iso_path: Path, *, verify_original_elf: bool = True) -> tuple[int, int, bytes]:
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
        if product_code != SUPPORTED_PRODUCT_CODE:
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
        if elf_hash != SUPPORTED_ELF_SHA256:
            raise PatchError(
                "unsupported or modified BOOT2 ELF SHA-256 "
                f"{elf_hash}; only the supported SLPM_650.06 revision is accepted"
            )
    return elf_offset, elf_size, elf


def parse_load_segment(elf: bytes) -> tuple[int, int, int, int, int]:
    if elf[:6] != b"\x7fELF\x01\x01":
        raise PatchError("boot executable is not ELF32 little-endian")
    fields = struct.unpack_from("<HHIIIIIHHHHHH", elf, 16)
    phoff, phentsize, phnum = fields[4], fields[8], fields[9]
    if phentsize < 32:
        raise PatchError("ELF program header entry is too small")
    loads = []
    for i in range(phnum):
        off = phoff + i * phentsize
        p_type, p_off, p_va, _p_pa, p_filesz, p_memsz, p_flags, _p_align = struct.unpack_from(
            "<IIIIIIII", elf, off
        )
        if p_type == 1:
            loads.append((p_off, p_va, p_filesz, p_memsz, p_flags))
    if loads != [(LOAD_FILE_OFFSET, LOAD_VA, LOAD_FILE_SIZE, 0x00CC518C, LOAD_FLAGS)]:
        raise PatchError(f"unexpected executable PT_LOAD layout: {loads!r}")
    return loads[0]


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


def va_to_file_offset(va: int, length: int, segment: tuple[int, int, int, int, int]) -> int:
    p_off, p_va, p_filesz, _p_memsz, p_flags = segment
    rel = va - p_va
    if rel < 0 or rel + length > p_filesz:
        raise PatchError(f"VA range {va:#x}+{length:#x} is outside file-backed PT_LOAD")
    if (p_flags & 1) == 0:
        raise PatchError(f"VA range {va:#x} is not in an executable PT_LOAD")
    return p_off + rel


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
    timing_values: tuple[int, ...] = CRTC_TIMING_VALUES,
) -> tuple[bytes, list[tuple[str, int]], int]:
    """Assemble a straight-line R5900 helper and append its aligned data table."""
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
    ri(0x0F, "t0", "zero", 0x1200, "lui t0,0x1200")
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
    rr("zero", "t2", "t2", 22, 0x00, "sll t2,t2,22 ; videoOutput bit 3 -> GCONT bit 25")
    rr("t1", "t2", "t1", 0, 0x25, "or t1,t1,t2 ; runtime GCONT")
    rr("t1", "zero", "t4", 0, 0x2D, "daddu t4,t1,zero ; retain final SMODE1")
    ri(0x0F, "t3", "zero", 1, "lui t3,0x0001")
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

    code_end = CRTC_CAVE_VA + len(code) * 4
    table_va = (code_end + 7) & ~7
    table_hi = (table_va >> 16) & 0xFFFF
    table_lo = table_va & 0xFFFF
    code[table_address_load_index] = encode_i(0x0F, 0, REG["t9"], table_hi)
    code[table_address_load_index + 1] = encode_i(0x0D, REG["t9"], REG["t9"], table_lo)
    listing[table_address_load_index] = (f"lui t9,0x{table_hi:04x}", code[table_address_load_index])
    listing[table_address_load_index + 1] = (f"ori t9,t9,0x{table_lo:04x}", code[table_address_load_index + 1])

    if len(timing_values) != len(CRTC_TIMING_VALUES):
        raise PatchError("unexpected number of CRTC timing values")
    table_values = (SMODE1_PROFILE_FINAL, *timing_values)
    code_bytes = struct.pack("<" + "I" * len(code), *code)
    pad = bytes(table_va - (CRTC_CAVE_VA + len(code_bytes)))
    table_bytes = struct.pack("<" + "Q" * len(table_values), *table_values)
    helper = code_bytes + pad + table_bytes
    if len(helper) > CRTC_CAVE_SIZE:
        raise PatchError(f"generated CRTC helper exceeds its cave: {len(helper):#x}")

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


def mips_control_targets(text: bytes):
    for off in range(0, len(text), 4):
        word = struct.unpack_from("<I", text, off)[0]
        pc = TEXT_VA + off
        op = word >> 26
        if op in (2, 3):
            yield pc, ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        elif op in (1, 4, 5, 6, 7):
            immediate = word & 0xFFFF
            if immediate & 0x8000:
                immediate -= 0x10000
            yield pc, pc + 4 + (immediate << 2)


def assert_cave_is_unused(
    elf: bytes,
    segment,
    va: int,
    size: int,
    *,
    scan_range_pointers: bool = False,
) -> None:
    file_off = va_to_file_offset(va, size, segment)
    if elf[file_off : file_off + size] != bytes(size):
        raise PatchError(f"code cave {va:#x}+{size:#x} is not zero-filled")
    text_off = LOAD_FILE_OFFSET
    text = elf[text_off : text_off + TEXT_SIZE]
    if len(text) != TEXT_SIZE:
        raise PatchError("unexpected .text size")
    for pc, target in mips_control_targets(text):
        if va <= target < va + size:
            raise PatchError(f"existing branch/jump enters cave from {pc:#x}")

    # Reject obvious static addresses formed by LUI followed by ADDIU/ORI, or
    # direct aligned 32-bit pointers anywhere in the file-backed ELF.
    words = struct.unpack("<" + "I" * (len(text) // 4), text)
    for index, word in enumerate(words):
        if word >> 26 != 0x0F:  # LUI
            continue
        reg = (word >> 16) & 31
        hi = word & 0xFFFF
        for j in range(index + 1, min(index + 12, len(words))):
            q = words[j]
            op, rs, rt, imm = q >> 26, (q >> 21) & 31, (q >> 16) & 31, q & 0xFFFF
            if rs != reg:
                continue
            if op == 0x09 and rt == reg:
                signed = imm - 0x10000 if imm & 0x8000 else imm
                target = ((hi << 16) + signed) & 0xFFFFFFFF
            elif op == 0x0D and rt == reg:
                target = (hi << 16) | imm
            else:
                continue
            if va <= target < va + size:
                raise PatchError(f"existing LUI address reference to cave at {target:#x}")

        # Catch direct stores using a high-address LUI base plus a store
        # displacement, even when the code never materializes a full pointer.
        for j in range(index + 1, min(index + 12, len(words))):
            q = words[j]
            op, rs, imm = q >> 26, (q >> 21) & 31, q & 0xFFFF
            if rs != reg or op not in (0x28, 0x29, 0x2B, 0x3F):
                continue
            displacement = imm - 0x10000 if imm & 0x8000 else imm
            target = ((hi << 16) + displacement) & 0xFFFFFFFF
            if va <= target < va + size:
                raise PatchError(f"existing direct store enters cave at {target:#x}")

    # Only aligned direct word pointers are meaningful as EE code/data
    # references. Bytewise hits in this ELF also occur inside packed assets.
    if scan_range_pointers:
        pointer_hits = [
            (off, struct.unpack_from("<I", elf, off)[0])
            for off in range(0, len(elf) - 3, 4)
            if va <= struct.unpack_from("<I", elf, off)[0] < va + size
        ]
        if pointer_hits:
            off, target = pointer_hits[0]
            raise PatchError(
                f"direct aligned pointer at ELF offset {off:#x} enters cave at {target:#x}"
            )
    else:
        direct_pointer = any(
            struct.unpack_from("<I", elf, off)[0] == va
            for off in range(0, len(elf) - 3, 4)
        )
        if direct_pointer:
            raise PatchError(f"direct file pointer to cave entry {va:#x} already exists")


def assert_cave_static_safety(elf: bytes, segment, va: int, size: int) -> None:
    """Check that the cave is a zero-filled .rodata hole below BSS."""
    sections = parse_sections(elf)
    rodata = sections.get(".rodata")
    bss = sections.get(".bss")
    if rodata is None or bss is None:
        raise PatchError("expected .rodata and .bss sections for code-cave audit")
    ro_flags, ro_va, _ro_off, ro_size = rodata
    _bss_flags, bss_va, _bss_off, bss_size = bss
    if (ro_flags & 0x2) == 0 or (ro_flags & 0x1) != 0:
        raise PatchError("CRTC cave is not in a non-writable allocated .rodata section")
    if not (ro_va <= va and va + size <= ro_va + ro_size):
        raise PatchError("CRTC cave is outside .rodata")
    if va < bss_va + bss_size and bss_va < va + size:
        raise PatchError("CRTC cave overlaps .bss/runtime allocation space")
    file_off = va_to_file_offset(va, size, segment)
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


def verify_iidx_pmode_source(elf: bytes, segment) -> None:
    """Require the game's PMODE builder and both register-write branches."""
    checks = (
        (0x00157FDC, 0x24020066, "display-environment PMODE value"),
        (0x00157FE0, 0xFE220000, "store PMODE value at display-env offset 0"),
        (0x00157460, 0xFC440000, "write display-env PMODE to GS in branch 1"),
        (0x001574A0, 0xFC640000, "write display-env PMODE to GS in branch 2"),
        (0x00157684, 0x0C055FE2, "first display environment uses PMODE builder"),
        (0x001576A0, 0x0C055FE2, "second display environment uses PMODE builder"),
        (0x0014F534, 0x08055D0C, "display update tail-calls GS writer"),
        (0x0014FC7C, 0x08055D0C, "alternate display update tail-calls GS writer"),
        (0x001578C8, 0x0C055D0C, "environment update calls GS writer"),
    )
    for va, word, reason in checks:
        require_word(elf, segment, va, word, reason)


def make_display_helper(display_value: int = DISPLAY_VALUE) -> bytes:
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
        encode_j(DISPLAY_CAVE_VA + 8 * 4, DISPLAY_HOOK_RETURN_VA), 0,
    )
    return struct.pack("<" + "I" * len(words), *words)


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


def make_patched_elf(elf: bytes, profile_name: str = "v1.0"):
    if profile_name not in PATCH_PROFILES:
        raise PatchError(f"unknown patch profile: {profile_name}")
    profile = PATCH_PROFILES[profile_name]
    segment = parse_load_segment(elf)
    verify_iidx_pmode_source(elf, segment)
    display_helper = make_display_helper(profile["display_value"])
    crtc_helper, listing, table_va = build_crtc_helper(profile["timing_values"])
    assert_cave_is_unused(elf, segment, DISPLAY_CAVE_VA, DISPLAY_CAVE_SIZE)
    assert_cave_is_unused(
        elf, segment, CRTC_CAVE_VA, CRTC_CAVE_SIZE, scan_range_pointers=True
    )
    assert_cave_static_safety(elf, segment, CRTC_CAVE_VA, CRTC_CAVE_SIZE)

    patched = bytearray(elf)
    rows = []
    instruction_patches = (
        (0x001001FC, 0x24060002, 0x24060050, "boot ResetGraph: NTSC to DTV 480p"),
        (0x0014F8BC, 0x24060002, 0x24060050, "game ResetGraph: NTSC to DTV 480p"),
        (0x00158018, 0x24040002, 0x24040050, "3rd DISPLAY env NTSC-shape branch for mode 0x50"),
        (
            DISPLAY_HOOK_VA,
            0xFE200020,
            encode_j(DISPLAY_HOOK_VA, DISPLAY_CAVE_VA),
            "existing DISPLAY code cave hook",
        ),
        (
            RESETGRAPH_TAIL_VA,
            encode_j(RESETGRAPH_TAIL_VA, SETGSCRT_WRAPPER_VA),
            encode_j(RESETGRAPH_TAIL_VA, CRTC_CAVE_VA),
            "ResetGraph tail to BIOS-aware CRTC helper",
        ),
    )
    for patch in instruction_patches:
        rows.append(patch_word(patched, segment, *patch))

    display_delay_off = va_to_file_offset(DISPLAY_HOOK_DELAY_VA, 4, segment)
    if bytes(elf[display_delay_off : display_delay_off + 4]) != struct.pack("<I", 0xDFBF0060):
        raise PatchError("DISPLAY hook delay slot is not the original ld ra,96(sp)")
    reset_delay_off = va_to_file_offset(RESETGRAPH_DELAY_VA, 4, segment)
    if bytes(elf[reset_delay_off : reset_delay_off + 4]) != struct.pack("<I", 0x27BD0080):
        raise PatchError("ResetGraph stack-restoring delay slot changed")
    wrapper_off = va_to_file_offset(SETGSCRT_WRAPPER_VA, 16, segment)
    expected_wrapper = (0x24030002, 0x0000000C, 0x03E00008, 0x00000000)
    if struct.unpack_from("<4I", elf, wrapper_off) != expected_wrapper:
        raise PatchError("SetGsCrt syscall wrapper preimage changed")

    display_off = va_to_file_offset(DISPLAY_CAVE_VA, len(display_helper), segment)
    patched[display_off : display_off + len(display_helper)] = display_helper
    crtc_off = va_to_file_offset(CRTC_CAVE_VA, len(crtc_helper), segment)
    patched[crtc_off : crtc_off + len(crtc_helper)] = crtc_helper
    rows.extend((
        (DISPLAY_CAVE_VA, bytes(len(display_helper)), display_helper, "existing DISPLAY helper"),
        (CRTC_CAVE_VA, bytes(len(crtc_helper)), crtc_helper, "BIOS-aware CRTC helper and value table"),
    ))
    return bytes(patched), rows, listing, table_va


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


def build(
    source: Path,
    output: Path,
    profile_name: str = "v1.0",
) -> tuple[str, str, str, int, list[tuple[str, int]]]:
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

    elf_iso_offset, elf_size, original_elf = locate_boot_elf(source)
    segment = parse_load_segment(original_elf)
    patched_elf, patch_rows, listing, table_va = make_patched_elf(original_elf, profile_name)
    patched_elf_hash = sha256_bytes(patched_elf)
    if patched_elf_hash != PATCHED_ELF_SHA256:
        raise PatchError(f"generated patched ELF hash is unexpected: {patched_elf_hash}")

    iso_ranges = []
    for va, _before, _after, _reason in patch_rows:
        # Every row's length is either one instruction or the exact cave payload.
        length = len(_after)
        elf_off = va_to_file_offset(va, length, segment)
        iso_ranges.append((elf_iso_offset + elf_off, length))
    allowed = merge_ranges(iso_ranges)

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
            elf_off = va_to_file_offset(va, len(after), segment)
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
        out_iso_offset, out_elf_size, out_elf = locate_boot_elf(
            output, verify_original_elf=False
        )
        if out_iso_offset != elf_iso_offset or out_elf_size != elf_size or out_elf != patched_elf:
            raise PatchError("final ISO BOOT2 verification failed")
        if sha256_bytes(out_elf) != PATCHED_ELF_SHA256:
            raise PatchError("final patched boot ELF hash verification failed")
        profile = PATCH_PROFILES[profile_name]
        return (
            source_hash_after,
            output_hash,
            sha256_bytes(out_elf),
            len(build_crtc_helper(profile["timing_values"])[0]),
            listing,
        )
    except Exception:
        partial.unlink(missing_ok=True)
        if published:
            output.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="your own IIDX 3rd Style ISO dump")
    parser.add_argument("--output", type=Path, help="new output ISO path; refuses to overwrite existing files")
    args = parser.parse_args()
    try:
        output_arg = args.output or args.source.with_name(args.source.stem + "_480p_v1.0.iso")
        source_hash, output_hash, elf_hash, helper_size, _listing = build(
            args.source, output_arg, "v1.0"
        )
        output = output_arg.resolve()
        profile = PATCH_PROFILES["v1.0"]
        print(f"STATE={profile['state']}")
        print(f"SOURCE={args.source.resolve()}")
        print(f"SOURCE_SHA256={source_hash}")
        print(f"OUTPUT={output}")
        print(f"OUTPUT_SIZE={output.stat().st_size}")
        print(f"OUTPUT_SHA256={output_hash}")
        print(f"PATCHED_ELF_SHA256={elf_hash}")
        print(f"CRTC_HELPER_VA={CRTC_CAVE_VA:#010x}")
        print(f"CRTC_HELPER_SIZE={helper_size}")
        print(f"CRTC_TABLE_VA={build_crtc_helper(profile['timing_values'])[2]:#010x}")
        print(f"DISPLAY_VALUE={profile['display_value']:#018x}")
        dx, dy, magh, magv, dw, dh = decode_display_value(profile["display_value"])
        print(
            f"DISPLAY_FIELDS=DX:{dx},DY:{dy},MAGH:{magh},MAGV:{magv},DW:{dw},DH:{dh},"
            f"source_rows:{(dh + 1) // (magv + 1)}"
        )
        print(f"SYNCV={profile['timing_values'][-1]:#018x}")
        print("BIOS_OSD_COLOR=preserved at runtime; no fixed RGB/component selection")
        print("PMODE=runtime game display-env restore; no GS PMODE readback")
        print("INPUT=ISO9660 SYSTEM.CNF BOOT2 extent discovered dynamically; full-ISO hash is informational")
        print("VERIFIED=ELF allowlist, MIPS preimages, code caves, patched ELF hash, and non-patch ISO bytes")
        return 0
    except (PatchError, OSError, struct.error, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
