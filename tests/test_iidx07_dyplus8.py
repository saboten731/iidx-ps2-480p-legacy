"""Focused static and instruction tests for the 7th Style DY+8 candidate."""

import os
import struct
import unittest
from pathlib import Path

import patch480p
from test_iidx06_256to480 import display, run_helper


SOURCE_ENV = "IIDX07_SOURCE_ISO"


class SeventhStyleTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = patch480p.TITLE_CONFIGS["SLPM_655.93"]
        cls.va = cls.config["display_cave_va"]
        cls.hooks = cls.config["display_hooks"]
        cls.helper, cls.listing = patch480p.make_dynamic_display_helper(
            cls.va, cls.config["display_cave_size"], cls.hooks,
            scale_256_rows=True, limit_256_to_480=True,
            only_256_rows=True, adjust_256_dy_plus8=True,
        )

    def test_guarded_256_input_adds_wrapped_dy_and_preserves_other_fields(self):
        self.assertEqual(len(self.helper), 0x90)
        self.assertEqual(self.config["display_cave_size"], 0x90)
        self.assertEqual(patch480p.decode_display_value(0x000FF4FF00823138),
                         (312, 35, 1, 0, 1279, 255))
        expected_example = 0x001DF4FF0882B138
        self.assertEqual(
            run_helper(
                self.helper, self.va, self.hooks[0],
                0x000FF4FF00823138, 0x12000080,
            ),
            expected_example,
        )
        self.assertEqual(
            patch480p.decode_display_value(expected_example),
            (312, 43, 1, 1, 1279, 479),
        )
        previous_helper, _ = patch480p.make_dynamic_display_helper(
            self.va, self.config["display_cave_size"], self.hooks,
            scale_256_rows=True, limit_256_to_480=True,
            only_256_rows=True,
        )
        for hook, address in zip(self.hooks, (0x12000080, 0x120000A0)):
            for dy in (0, 17, 35, 2040, 2047):
                dx, magh, dw = 312, 1, 1279
                source = display(dx, dy, 1, 0, 1279, 255)
                with self.subTest(hook=hex(hook[0]), dx=dx, dy=dy):
                    self.assertEqual(
                        run_helper(self.helper, self.va, hook, source, address),
                        display(dx, (dy + 8) & 0x7FF, magh, 1, dw, 479),
                    )
            source = display(312, 35, 1, 0, 1279, 255)
            reserved = (0x1FF << 55) | (0x7 << 29)
            source |= reserved
            self.assertEqual(
                run_helper(self.helper, self.va, hook, source, address),
                display(312, 43, 1, 1, 1279, 479) | reserved,
            )
            for magv, dh in ((0, 223), (0, 239), (0, 100), (1, 255), (2, 255)):
                source = display(312, 35, 1, magv, 1279, dh)
                with self.subTest(hook=hex(hook[0]), magv=magv, dh=dh):
                    self.assertEqual(
                        run_helper(self.helper, self.va, hook, source, address),
                        source,
                    )
                    self.assertEqual(
                        run_helper(previous_helper, self.va, hook, source, address),
                        source,
                    )

    def test_helper_keeps_cave_size_and_title_specific_delta(self):
        self.assertTrue(self.config["display_256_dy_plus8"])
        self.assertEqual(len(self.helper), self.config["display_cave_size"])
        instructions = [text for text, _ in self.listing]
        for expected in (
            "dsrl32 t0,t7,12",
            "andi t0,t0,0x07ff",
            "addiu t1,zero,255",
            "bne t0,t1,store_display",
            "addiu t1,zero,0x120",
            "dsrl t2,t7,12 ; source DY",
            "andi t2,t2,0x07ff",
            "addiu t1,t2,8",
            "andi t1,t1,0x07ff",
        ):
            self.assertIn(expected, instructions)

    def test_non_target_outputs_match_the_existing_trial01_helper(self):
        trial01_env = os.environ.get("IIDX07_TRIAL01_ISO")
        if not trial01_env:
            self.skipTest("set IIDX07_TRIAL01_ISO for optional comparison")
        trial01 = Path(trial01_env)
        self.assertTrue(trial01.is_file(), trial01)
        _, _, elf, product_code = patch480p.locate_boot_elf(
            trial01, verify_original_elf=False,
        )
        self.assertEqual(product_code, "SLPM_655.93")
        segment = patch480p.parse_title_load_segment(elf, product_code)
        helper_offset = patch480p.va_to_file_offset(
            self.va, self.config["display_cave_size"], segment,
        )
        trial01_helper = elf[
            helper_offset:helper_offset + self.config["display_cave_size"]
        ]
        self.assertEqual(len(trial01_helper), 0x90)

        non_target_values = (
            display(312, 35, 1, 0, 1279, 223),
            display(312, 35, 1, 0, 1279, 239),
            display(312, 35, 1, 0, 1279, 100),
            display(312, 35, 1, 1, 1279, 255),
            display(312, 35, 1, 2, 1279, 255),
        )
        reserved = (0x1FF << 55) | (0x7 << 29)
        for hook, address in zip(self.hooks, (0x12000080, 0x120000A0)):
            for original in non_target_values:
                source = original | reserved
                with self.subTest(hook=hex(hook[0]), source=hex(source)):
                    old_output = run_helper(
                        trial01_helper, self.va, hook, source, address,
                    )
                    new_output = run_helper(
                        self.helper, self.va, hook, source, address,
                    )
                    self.assertEqual(old_output, source)
                    self.assertEqual(new_output, old_output)

    @unittest.skipUnless(os.environ.get(SOURCE_ENV), f"set {SOURCE_ENV} to original 7th ISO")
    def test_elf_store_builder_caves_and_crtc_guard(self):
        _, _, elf, code = patch480p.locate_boot_elf(Path(os.environ[SOURCE_ENV]))
        self.assertEqual(code, "SLPM_655.93")
        segment = patch480p.parse_title_load_segment(elf, code)

        def word(va):
            offset = patch480p.va_to_file_offset(va, 4, segment)
            return struct.unpack_from("<I", elf, offset)[0]

        preimages = {
            0x0012AA40: 0x24060002,  # ResetGraph NTSC becomes mode 80
            0x001003EC: 0xA6120002,  # mode stored in GS environment
            0x00100668: 0x96240002,  # DISPLAY builder reads that mode
            0x0012AA70: 0x24060280,  # builder width 640
            0x0012AA78: 0x24070100,  # builder height 256
            0x0012AAA0: 0x0C0403BA,  # builder call
            0x001009B8: 0xFC440000,  # PMODE1
            0x001009BC: 0x34630070,  # DISPFB1 address
            0x001009C0: 0x34C60080,  # DISPLAY1 address
            0x001009D0: 0xFC650000,  # DISPFB1 store
            0x001009D4: 0xDE020018,  # DISPLAY1 value
            0x001009D8: 0xFCC20000,  # DISPLAY1 store
            0x001009DC: 0xDE030020,  # DISPLAY1 delay slot
            0x001009F8: 0xFC640000,  # PMODE2
            0x00100A00: 0x34C60090,  # DISPFB2 address
            0x00100A0C: 0x34A500A0,  # DISPLAY2 address
            0x00100A20: 0xFCC20000,  # DISPFB2 store
            0x00100A24: 0xDE030018,  # DISPLAY2 value
            0x00100A28: 0xFCA30000,  # DISPLAY2 store
            0x00100A2C: 0xDE020020,  # DISPLAY2 delay slot
            0x002E0FC8: 0x5290DD24,  # pre-existing branch to CRTC guard
            0x002D845C: 0,
            0x002D8460: 0,
        }
        for va, expected in preimages.items():
            with self.subTest(va=hex(va)):
                self.assertEqual(word(va), expected)

        for kind in ("display", "crtc"):
            patch480p.assert_title_cave_is_unused(
                elf, segment, self.config,
                self.config[kind + "_cave_va"],
                self.config[kind + "_cave_size"],
            )
        source_va = 0x002E0FC8
        branch_imm = word(source_va) & 0xFFFF
        branch_imm -= 0x10000 if branch_imm & 0x8000 else 0
        self.assertEqual(source_va + 4 + (branch_imm << 2), 0x002D845C)
        crtc, _ = patch480p.build_crtc_helper(
            self.config["crtc_cave_va"], self.config["setgscrt_wrapper_va"],
        )
        self.assertEqual(len(crtc), 180)
        patched, rows, _ = patch480p.make_patched_elf_for_title(elf, code)
        self.assertEqual(patch480p.sha256_bytes(patched),
                         self.config["patched_elf_sha256"])
        guard_offset = patch480p.va_to_file_offset(0x002D845C, 8, segment)
        self.assertEqual(struct.unpack_from("<2I", patched, guard_offset), (
            patch480p.encode_j(0x002D845C, 0x002D8464 + len(crtc)), 0,
        ))
        for va in (0x001009D0, 0x00100A20):
            offset = patch480p.va_to_file_offset(va, 4, segment)
            self.assertEqual(patched[offset:offset + 4], elf[offset:offset + 4])
        self.assertEqual({row[0] for row in rows}, {
            0x0012AA40, 0x002D845C, 0x00100450, 0x001004C8,
            0x001009D8, 0x00100A28, 0x001F0630, 0x002D8464,
        })


if __name__ == "__main__":
    unittest.main()
