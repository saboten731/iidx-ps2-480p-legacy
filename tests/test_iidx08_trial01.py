"""Focused 8th Style trial02 checks against trial01 and the original ELF."""

import os
import struct
import unittest
from pathlib import Path

import patch480p
from test_iidx06_256to480 import display, run_helper


CODE = "SLPM_657.68"
SOURCE_ENV = "IIDX08_SOURCE_ISO"
TRIAL01_ENV = "IIDX08_TRIAL01_ISO"


class EighthStyleTrial02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = patch480p.TITLE_CONFIGS[CODE]
        cls.va = cls.config["display_cave_va"]
        cls.hooks = cls.config["display_hooks"]
        cls.helper, cls.listing = patch480p.make_dynamic_display_helper(
            cls.va,
            cls.config["display_cave_size"],
            cls.hooks,
            scale_256_rows=True,
            limit_256_to_480=True,
            only_256_rows=True,
            adjust_256_dy_plus8=cls.config["display_256_dy_plus8"],
        )

    def test_both_display_entries_apply_dy_plus8_only_to_256_rows(self):
        self.assertEqual(len(self.helper), 0x90)
        self.assertTrue(self.config["display_only_256_rows"])
        self.assertTrue(self.config["display_256_dy_plus8"])
        self.assertNotIn("display_256_dy_plus18", self.config)
        self.assertNotIn("display_256_horizontal_fix", self.config)

        for hook, address in zip(self.hooks, (0x12000080, 0x120000A0)):
            for dx, dy, magh, dw in (
                (312, 35, 1, 1279),
                (320, 2040, 1, 1279),
                (320, 2047, 1, 1279),
            ):
                source = display(dx, dy, magh, 0, dw, 255)
                source |= (0x1FF << 55) | (0x7 << 29)
                with self.subTest(hook=hex(hook[0]), dy=dy):
                    actual, regs = run_helper(
                        self.helper, self.va, hook, source, address, return_regs=True
                    )
                    self.assertEqual(
                        actual,
                        display(dx, (dy + 8) & 0x7FF, magh, 1, dw, 479)
                        | (0x1FF << 55) | (0x7 << 29),
                    )
                    self.assertEqual(regs[patch480p.REG["t0"]], 255)
                    self.assertEqual(regs[patch480p.REG["t2"]], 0x08000000)
            for magv, dh in ((0, 223), (0, 239), (0, 100), (1, 255), (2, 255)):
                source = display(312, 35, 1, magv, 1279, dh)
                with self.subTest(hook=hex(hook[0]), magv=magv, dh=dh):
                    self.assertEqual(
                        run_helper(self.helper, self.va, hook, source, address),
                        source,
                    )

    def test_non_target_outputs_match_trial01_helper(self):
        trial01_path = os.environ.get(TRIAL01_ENV)
        if not trial01_path:
            self.skipTest("set IIDX08_TRIAL01_ISO for optional comparison")
        trial01 = Path(trial01_path)
        if not trial01.is_file():
            self.skipTest("trial01 ISO is optional local comparison evidence")
        _, _, elf, code = patch480p.locate_boot_elf(trial01, verify_original_elf=False)
        self.assertEqual(code, CODE)
        segment = patch480p.parse_title_load_segment(elf, code)
        offset = patch480p.va_to_file_offset(
            self.va, self.config["display_cave_size"], segment
        )
        trial01_helper = elf[offset:offset + self.config["display_cave_size"]]
        self.assertEqual(len(trial01_helper), 0x90)

        cases = (
            display(312, 35, 1, 0, 1279, 223),
            display(312, 35, 1, 0, 1279, 239),
            display(312, 35, 1, 0, 1279, 100),
            display(312, 35, 1, 1, 1279, 255),
            display(312, 35, 1, 2, 1279, 255),
        )
        for hook, address in zip(self.hooks, (0x12000080, 0x120000A0)):
            for source in cases:
                with self.subTest(hook=hex(hook[0]), source=hex(source)):
                    actual, actual_regs = run_helper(
                        self.helper, self.va, hook, source, address, return_regs=True
                    )
                    old, old_regs = run_helper(
                        trial01_helper, self.va, hook, source, address, return_regs=True
                    )
                    self.assertEqual(actual, old)
                    self.assertEqual(actual_regs, old_regs)

    @unittest.skipUnless(os.environ.get("IIDX08_TRIAL_ISO"),
                         "set IIDX08_TRIAL_ISO to the generated trial ISO")
    def test_generated_iso_is_rejected_as_an_original(self):
        self.assertIn(
            "7134FF3E2FE82EE047AE211E1CC8ADEF60651F30EEE56142C0557737002F8875",
            patch480p.ALREADY_PATCHED_ELF_SHA256S,
        )
        trial_paths = [Path(os.environ["IIDX08_TRIAL_ISO"])]
        if os.environ.get(TRIAL01_ENV):
            trial_paths.append(Path(os.environ[TRIAL01_ENV]))
        for trial_path in trial_paths:
            with self.subTest(path=str(trial_path)):
                with self.assertRaisesRegex(patch480p.PatchError, "already patched"):
                    patch480p.locate_boot_elf(trial_path)

    @unittest.skipUnless(os.environ.get(SOURCE_ENV), f"set {SOURCE_ENV} to original 8th ISO")
    def test_original_elf_mode_writer_hooks_and_caves(self):
        _, _, elf, code = patch480p.locate_boot_elf(Path(os.environ[SOURCE_ENV]))
        self.assertEqual(code, CODE)
        segment = patch480p.parse_title_load_segment(elf, code)

        def word(va):
            offset = patch480p.va_to_file_offset(va, 4, segment)
            return struct.unpack_from("<I", elf, offset)[0]

        # ResetGraph stores mode 80 in the game environment. The sole direct
        # display-builder caller supplies 640x256 and zero position offsets.
        # In the mode-80 path, the game computes MAGH=1, DW=2*640-1,
        # DH=256-1 and nominal DX=312, DY=35 plus runtime offsets.
        preimages = {
            0x0010035C: 0xA6120002,
            0x001005D8: 0x96240002,
            0x00100680: 0x14A4002B,
            0x00100734: 0x14A20043,
            0x00100738: 0x24020050,
            0x00100844: 0x14A2001E,
            0x0010084C: 0x240202D0,
            0x0010088C: 0x00031B3C,
            0x00100890: 0x0006303C,
            0x0010089C: 0x3C020080,
            0x001008BC: 0xFE630018,
            0x00100ED4: 0x0C040160,
            0x00100EF0: 0x0C040160,
            0x0012AF00: 0x24060002,
            0x0012AF08: 0x0C0400B2,
            0x0012AF64: 0x24060280,
            0x0012AF68: 0x24070100,
            0x0012AF6C: 0x0000402D,
            0x0012AF70: 0x0000482D,
            0x0012AF78: 0x0C040396,
            0x00100928: 0xFC440000,  # PMODE1
            0x0010092C: 0x34630070,  # DISPFB1 address
            0x00100930: 0x34C60080,  # DISPLAY1 address
            0x00100940: 0xFC650000,  # DISPFB1 store
            0x00100944: 0xDE020018,  # DISPLAY1 value
            0x00100948: 0xFCC20000,  # DISPLAY1 store
            0x0010094C: 0xDE030020,  # delay slot
            0x00100950: 0xFC830000,  # return
            0x00100968: 0xFC640000,  # PMODE2
            0x00100970: 0x34C60090,  # DISPFB2 address
            0x0010097C: 0x34A500A0,  # DISPLAY2 address
            0x00100990: 0xFCC20000,  # DISPFB2 store
            0x00100994: 0xDE030018,  # DISPLAY2 value
            0x00100998: 0xFCA30000,  # DISPLAY2 store
            0x0010099C: 0xDE020020,  # delay slot
            0x001009A0: 0xFC820000,  # return
        }
        for va, expected in preimages.items():
            with self.subTest(va=hex(va)):
                self.assertEqual(word(va), expected)

        self.assertEqual(self.config["crtc_cave_va"] + self.config["crtc_cave_size"], self.va)
        crtc, _, _ = patch480p.build_crtc_helper(
            self.config["timing_values"], self.config["crtc_cave_va"]
        )
        self.assertEqual(len(crtc), 0xF8)
        for kind in ("display", "crtc"):
            patch480p.assert_title_cave_is_unused(
                elf, segment, self.config,
                self.config[kind + "_cave_va"],
                self.config[kind + "_cave_size"],
            )

        patched, rows, _, _ = patch480p.make_patched_elf_profiled_title(elf, code)
        self.assertEqual(patch480p.sha256_bytes(patched),
                         self.config["patched_elf_sha256"])
        self.assertEqual({row[0] for row in rows}, {
            0x0012AF00, 0x001003C0, 0x00100438,
            0x00100948, 0x00100998, 0x0021D810, 0x0021D908,
        })
        for va in (0x00100940, 0x00100990, 0x0010094C, 0x0010099C):
            offset = patch480p.va_to_file_offset(va, 4, segment)
            self.assertEqual(patched[offset:offset + 4], elf[offset:offset + 4])


if __name__ == "__main__":
    unittest.main()
