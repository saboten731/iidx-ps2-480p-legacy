import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import patch480p


class PatchProfileTests(unittest.TestCase):
    @staticmethod
    def _directory_record(name, lba, length, *, is_directory=False):
        encoded = name if isinstance(name, bytes) else name.encode("ascii")
        record_size = 33 + len(encoded) + (1 if len(encoded) % 2 == 0 else 0)
        record = bytearray(record_size)
        record[0] = record_size
        struct.pack_into("<I", record, 2, lba)
        struct.pack_into("<I", record, 10, length)
        record[25] = 2 if is_directory else 0
        record[32] = len(encoded)
        record[33 : 33 + len(encoded)] = encoded
        return bytes(record)

    def _make_minimal_boot_iso(self, directory, boot_code="SLPM_650.06"):
        sector_size = patch480p.SECTOR_SIZE
        root_lba, cnf_lba, boot_lba = 20, 21, 22
        cnf = f"BOOT2 = cdrom0:\\{boot_code};1\n".encode("ascii")
        root = bytearray(sector_size)
        entries = (
            self._directory_record("SYSTEM.CNF;1", cnf_lba, len(cnf)),
            self._directory_record(f"{boot_code};1", boot_lba, 4),
        )
        offset = 0
        for entry in entries:
            root[offset : offset + len(entry)] = entry
            offset += len(entry)

        iso = bytearray(23 * sector_size)
        pvd = memoryview(iso)[16 * sector_size : 17 * sector_size]
        pvd[:7] = b"\x01CD001\x01"
        root_record = self._directory_record(b"\x00", root_lba, sector_size, is_directory=True)
        pvd[156 : 156 + len(root_record)] = root_record
        iso[root_lba * sector_size : (root_lba + 1) * sector_size] = root
        iso[cnf_lba * sector_size : cnf_lba * sector_size + len(cnf)] = cnf
        iso[boot_lba * sector_size : boot_lba * sector_size + 4] = b"ELF!"
        path = Path(directory) / "minimal-boot.iso"
        path.write_bytes(iso)
        return path

    def test_unknown_boot_executable_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            iso = self._make_minimal_boot_iso(temp_dir, "SLPM_699.99")
            with self.assertRaisesRegex(patch480p.PatchError, "unsupported BOOT2 executable"):
                patch480p.locate_boot_elf(iso)

    def test_elf_from_another_supported_title_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            iso = self._make_minimal_boot_iso(temp_dir, "SLPM_650.49")
            fourth_style_elf_hash = patch480p.TITLE_CONFIGS["SLPM_650.26"]["elf_sha256"]
            with patch.object(patch480p, "sha256_bytes", return_value=fourth_style_elf_hash):
                with self.assertRaisesRegex(
                    patch480p.PatchError,
                    "unsupported or modified BOOT2 ELF SHA-256",
                ):
                    patch480p.locate_boot_elf(iso)

    def test_known_patched_elf_is_rejected(self):
        patched_hash = patch480p.TITLE_CONFIGS["SLPM_650.26"]["patched_elf_sha256"]
        with tempfile.TemporaryDirectory() as temp_dir:
            iso = self._make_minimal_boot_iso(temp_dir)
            with patch.object(patch480p, "sha256_bytes", return_value=patched_hash):
                with self.assertRaisesRegex(patch480p.PatchError, "already patched"):
                    patch480p.locate_boot_elf(iso)

    def test_mismatched_instruction_preimage_is_rejected(self):
        segment = (0, 0x00100000, 4, 4, 0x7)
        elf = bytearray(4)
        with self.assertRaisesRegex(patch480p.PatchError, "preimage mismatch"):
            patch480p.patch_word(
                elf,
                segment,
                0x00100000,
                0x24060002,
                0x24060050,
                "synthetic preimage rejection test",
            )

    def test_stripped_cave_rejects_lui_address_written_to_another_register(self):
        segment = (0, 0x00100000, 0x400, 0x400, 0x7)
        elf = bytearray(0x400)
        # lui t0,0x0010; addiu t1,t0,0x0200; jr t1; nop
        # The pointer is built in t1, so a verifier that only accepts rt == t0
        # would miss this indirect entry into the cave at 0x00100200.
        struct.pack_into("<4I", elf, 0, 0x3C080010, 0x25090200, 0x01200008, 0)
        with self.assertRaisesRegex(
            patch480p.PatchError, "LUI-derived address reference to code cave"
        ):
            patch480p.assert_title_cave_is_unused(
                bytes(elf),
                [segment],
                {"stripped": True},
                0x00100200,
                0x20,
            )

    def test_insufficient_output_space_is_rejected_with_headroom(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.iso"
            output = Path(temp_dir) / "output.iso"
            source.write_bytes(b"source image")
            source_size = source.stat().st_size
            required = source_size + max(
                patch480p.MIN_OUTPUT_SPACE_MARGIN, source_size // 100
            )
            with patch.object(
                patch480p.shutil,
                "disk_usage",
                return_value=SimpleNamespace(free=required - 1),
            ):
                with self.assertRaisesRegex(
                    patch480p.PatchError, "insufficient free disk space"
                ):
                    patch480p.build(source, output)
            self.assertFalse(output.exists())
            self.assertFalse(Path(str(output) + ".partial").exists())

    def test_crtc_helpers_fit_and_never_read_pmode(self):
        default_timing = patch480p.PATCH_PROFILES["v1.0"]["timing_values"]
        for product_code, config in patch480p.TITLE_CONFIGS.items():
            with self.subTest(product_code=product_code):
                cave_va = config.get("crtc_cave_va", patch480p.CRTC_CAVE_VA)
                cave_size = config.get("crtc_cave_size", patch480p.CRTC_CAVE_SIZE)
                timing = config.get("timing_values", default_timing)
                helper, listing, _table_va = patch480p.build_crtc_helper(timing, cave_va)
                self.assertLessEqual(len(helper), cave_size)

                for offset in range(0, len(listing) * 4, 4):
                    word = struct.unpack_from("<I", helper, offset)[0]
                    is_ld_from_gs_pmode = (
                        word >> 26 == 0x37
                        and (word >> 21) & 31 == patch480p.REG["t0"]
                        and word & 0xFFFF == patch480p.GS_PMODE_OFFSET
                    )
                    self.assertFalse(is_ld_from_gs_pmode)

    def test_dynamic_display_helpers_fit_each_title_cave(self):
        dynamic_profiles = {
            code: config
            for code, config in patch480p.TITLE_CONFIGS.items()
            if config.get("display_mode") == "dynamic_240_or_224_rows"
        }
        self.assertEqual(set(dynamic_profiles), {"SLPM_651.56", "SLPM_655.93", "SLPM_657.68"})

        for product_code, config in dynamic_profiles.items():
            with self.subTest(product_code=product_code):
                helper, listing = patch480p.make_dynamic_display_helper(
                    config["display_cave_va"],
                    config["display_cave_size"],
                    config["display_hooks"],
                )
                self.assertEqual(len(helper), config["display_cave_size"])
                instructions = [text for text, _word in listing]
                self.assertIn("beq t0,t1,scale_display", instructions)
                self.assertIn("bne t0,t1,store_display", instructions)
                self.assertIn("sd t7,0(t8)", instructions)
                self.assertIn("jr t9", instructions)
                jr_words = [word for text, word in listing if text == "jr t9"]
                self.assertEqual(len(jr_words), 1)
                jr_word = jr_words[0]
                self.assertEqual((jr_word >> 21) & 31, patch480p.REG["t9"])
                self.assertEqual((jr_word >> 16) & 31, 0)
                self.assertEqual((jr_word >> 11) & 31, 0)
                self.assertEqual((jr_word >> 6) & 31, 0)
                self.assertEqual(jr_word & 63, 0x08)


if __name__ == "__main__":
    unittest.main()
