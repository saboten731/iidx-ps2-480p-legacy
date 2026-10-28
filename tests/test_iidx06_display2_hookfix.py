import os
import struct
import unittest
from pathlib import Path

import patch480p


SOURCE_ISO = Path(os.environ["IIDX06_SOURCE_ISO"]) if "IIDX06_SOURCE_ISO" in os.environ else None


class Iidx06Display2HookFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE_ISO is None:
            raise unittest.SkipTest("set IIDX06_SOURCE_ISO to your own original 6th Style ISO")
        _, _, cls.elf, product_code = patch480p.locate_boot_elf(SOURCE_ISO)
        cls.config = patch480p.TITLE_CONFIGS[product_code]
        cls.segment = patch480p.parse_title_load_segment(cls.elf, product_code)

    @classmethod
    def original_word(cls, va):
        offset = patch480p.va_to_file_offset(va, 4, cls.segment)
        return struct.unpack_from("<I", cls.elf, offset)[0]

    def test_second_hook_moves_from_dispfb2_to_display2(self):
        # The game's second path loads DISPFB2 and DISPLAY2 from different
        # display-environment fields and constructs distinct GS addresses.
        original = {
            0x001AA00C: 0x3C061200,  # lui a2,0x1200
            0x001AA018: 0x34C60090,  # ori a2,a2,0x0090: DISPFB2
            0x001AA01C: 0x3C051200,  # lui a1,0x1200
            0x001AA024: 0x34A500A0,  # ori a1,a1,0x00a0: DISPLAY2
            0x001AA034: 0xDE020010,  # ld v0,0x10(s0): DISPFB value
            0x001AA038: 0xFCC20000,  # sd v0,0(a2): DISPFB2
            0x001AA03C: 0xDE030018,  # ld v1,0x18(s0): DISPLAY value
            0x001AA040: 0xFCA30000,  # sd v1,0(a1): DISPLAY2
            0x001AA044: 0xDE020020,  # ld v0,0x20(s0): preserved delay slot
            0x001AA048: 0xFC820000,  # sd v0,0(a0): following write
        }
        for va, expected in original.items():
            with self.subTest(va=f"{va:08X}"):
                self.assertEqual(self.original_word(va), expected)

        second_hook = self.config["display_hooks"][1]
        self.assertEqual(second_hook, (
            0x001AA040, 0x001AA044, 0xFCA30000, 0xDE020020,
            0x18, 0x001AA048, "v1", "a1",
        ))
        patched, _, _ = patch480p.make_patched_elf_for_title(self.elf, "SLPM_651.56")
        for va in (0x001AA038, 0x001AA03C, 0x001AA044, 0x001AA048):
            offset = patch480p.va_to_file_offset(va, 4, self.segment)
            self.assertEqual(struct.unpack_from("<I", patched, offset)[0], original[va])
        offset = patch480p.va_to_file_offset(0x001AA040, 4, self.segment)
        self.assertEqual(
            struct.unpack_from("<I", patched, offset)[0],
            patch480p.encode_j(0x001AA040, 0x002E9120 + 0x18),
        )

    def test_second_helper_entry_preserves_common_scaler_and_returns(self):
        cave_va = self.config["display_cave_va"]
        cave_size = self.config["display_cave_size"]
        new_helper, listing = patch480p.make_dynamic_display_helper(
            cave_va, cave_size, self.config["display_hooks"]
        )
        previous_hooks = (
            self.config["display_hooks"][0],
            (0x001AA038, 0x001AA03C, 0xFCC20000, 0xDE030018,
             0x18, 0x001AA040, "v0", "a2"),
        )
        old_helper, _ = patch480p.make_dynamic_display_helper(
            cave_va, cave_size, previous_hooks
        )
        self.assertEqual(len(new_helper), 0xF0)
        self.assertEqual(new_helper[:0x18], old_helper[:0x18])
        self.assertEqual(new_helper[0x30:], old_helper[0x30:])
        self.assertEqual([text for text, _ in listing[6:12]], [
            "daddu t7,v1,zero", "daddu t8,a1,zero",
            "lui t9,0x001a", "ori t9,t9,0xa048",
            "j 0x002e9150", "nop",
        ])
        self.assertEqual(listing[6][1], patch480p.encode_r(
            0, patch480p.REG["v1"], patch480p.REG["t7"], 0, 0x2D
        ))
        self.assertEqual(listing[7][1], patch480p.encode_r(
            0, patch480p.REG["a1"], patch480p.REG["t8"], 0, 0x2D
        ))
        self.assertEqual(listing[10][1], patch480p.encode_j(cave_va + 0x28, cave_va + 0x30))
        self.assertEqual(listing[11][1], 0)
        self.assertEqual(listing[32][0], "jr t9")
        self.assertEqual(listing[33][1], 0)


if __name__ == "__main__":
    unittest.main()
