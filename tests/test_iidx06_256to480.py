"""Execute the emitted 6th DISPLAY helper, including MIPS delay slots."""

import hashlib
import struct
import unittest

import patch480p


MASK64 = (1 << 64) - 1


def signed(value, bits):
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def display(dx, dy, magh, magv, dw, dh):
    return dx | (dy << 12) | (magh << 23) | (magv << 27) | (dw << 32) | (dh << 44)


def run_helper(payload, cave_va, hook, value, gs_address, *, return_regs=False):
    """Interpret the emitted instruction subset and require one GS write."""
    _, _, _, _, entry, return_va, source, address = hook
    regs = [0] * 32
    regs[patch480p.REG[source]] = value
    regs[patch480p.REG[address]] = gs_address
    words = struct.unpack(f"<{len(payload) // 4}I", payload)
    writes = []
    pc = cave_va + entry
    pending = None

    for _ in range(100):
        if not cave_va <= pc < cave_va + len(payload):
            assert pc == return_va, (hex(pc), hex(return_va))
            assert len(writes) == 1 and writes[0][0] == gs_address, writes
            if return_regs:
                return writes[0][1], regs
            return writes[0][1]

        word = words[(pc - cave_va) // 4]
        op = word >> 26
        rs, rt, rd = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        sa, fn, imm = (word >> 6) & 31, word & 63, word & 0xFFFF
        previous_target = pending
        pending = None
        next_target = None

        if word == 0:
            pass
        elif op == 0:
            if fn == 0x2D:  # daddu
                regs[rd] = (regs[rs] + regs[rt]) & MASK64
            elif fn == 0x25:  # or
                regs[rd] = regs[rs] | regs[rt]
            elif fn == 0x26:  # xor
                regs[rd] = regs[rs] ^ regs[rt]
            elif fn == 0x38:  # dsll
                regs[rd] = (regs[rt] << sa) & MASK64
            elif fn == 0x3A:  # dsrl
                regs[rd] = regs[rt] >> sa
            elif fn == 0x3C:  # dsll32
                regs[rd] = (regs[rt] << (32 + sa)) & MASK64
            elif fn == 0x3E:  # dsrl32
                regs[rd] = regs[rt] >> (32 + sa)
            elif fn == 0x08:  # jr
                next_target = regs[rs]
            else:
                raise AssertionError(f"unknown R instruction {word:08X} at {pc:08X}")
        elif op == 0x0F:  # lui
            regs[rt] = signed((imm << 16) & 0xFFFFFFFF, 32) & MASK64
        elif op == 0x0D:  # ori
            regs[rt] = regs[rs] | imm
        elif op == 0x0E:  # xori
            regs[rt] = regs[rs] ^ imm
        elif op == 0x0C:  # andi
            regs[rt] = regs[rs] & imm
        elif op == 0x09:  # addiu
            regs[rt] = (regs[rs] + signed(imm, 16)) & MASK64
        elif op in (0x04, 0x05):  # beq / bne
            take = regs[rs] == regs[rt]
            if (op == 0x04 and take) or (op == 0x05 and not take):
                next_target = pc + 4 + (signed(imm, 16) << 2)
        elif op == 0x02:  # j
            next_target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        elif op == 0x3F:  # sd
            writes.append(((regs[rs] + signed(imm, 16)) & MASK64, regs[rt] & MASK64))
        else:
            raise AssertionError(f"unknown opcode {op:02X} at {pc:08X}")

        regs[0] = 0
        if previous_target is not None:
            pc = previous_target
        else:
            pc += 4
            pending = next_target
    raise AssertionError("helper failed to return")


class Iidx06Scale256To480DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = patch480p.TITLE_CONFIGS["SLPM_651.56"]
        cls.va = cls.config["display_cave_va"]
        cls.hooks = cls.config["display_hooks"]
        cls.baseline, _ = patch480p.make_dynamic_display_helper(
            cls.va, cls.config["display_cave_size"], cls.hooks
        )
        cls.previous_512, _ = patch480p.make_dynamic_display_helper(
            cls.va, cls.config["display_cave_size"], cls.hooks,
            scale_256_rows=cls.config["display_scale_256_rows"],
        )
        cls.trial, cls.listing = patch480p.make_dynamic_display_helper(
            cls.va, cls.config["display_cave_size"], cls.hooks,
            scale_256_rows=cls.config["display_scale_256_rows"],
            limit_256_to_480=cls.config["display_256_to_480"],
        )
        cls.trial_dyplus18, cls.dy_listing = patch480p.make_dynamic_display_helper(
            cls.va, cls.config["display_cave_size"], cls.hooks,
            scale_256_rows=cls.config["display_scale_256_rows"],
            limit_256_to_480=cls.config["display_256_to_480"],
            adjust_256_dy_plus18=cls.config["display_256_dy_plus18"],
        )

    def test_cave_entries_and_branch_delay_slots(self):
        self.assertEqual(len(self.trial), self.config["display_cave_size"])
        self.assertEqual(len(self.trial_dyplus18), self.config["display_cave_size"])
        self.assertEqual(self.trial[:0x30], self.baseline[:0x30])
        self.assertEqual(hashlib.sha256(self.baseline[:0x90]).hexdigest().upper(),
                         "E7A0E65F75467A37377A25EF37EBA75EC04F61FCD7A391EC52501C88842D7FB3")
        words = struct.unpack(f"<{len(self.trial) // 4}I", self.trial)
        labels = [text for text, _ in self.listing]
        self.assertEqual(labels[33:36], ["sd t7,0(t8)", "jr t9", "nop"])
        self.assertEqual(words[5], 0)  # DISPLAY1 jump delay slot
        self.assertEqual(words[11], 0)  # DISPLAY2 jump delay slot
        self.assertEqual(words[20], patch480p.encode_i(0x09, 0, patch480p.REG["t1"], 223))
        self.assertEqual(words[22], patch480p.encode_i(0x09, 0, patch480p.REG["t1"], 255))
        self.assertEqual(words[28], patch480p.encode_i(0x0D, patch480p.REG["t1"], patch480p.REG["t1"], 0x20))
        for index, target in ((14, 33), (19, 25), (21, 25), (23, 33)):
            self.assertEqual(index + 1 + signed(words[index] & 0xFFFF, 16), target)
        self.assertEqual(words[24], 0)  # final branch delay slot
        self.assertEqual(words[25] >> 26, 0)  # scale path begins with dsll
        for code, config in patch480p.TITLE_CONFIGS.items():
            if code not in ("SLPM_651.56", "SLPM_655.93", "SLPM_657.68"):
                self.assertNotIn("display_scale_256_rows", config)
                self.assertNotIn("display_256_to_480", config)
            if code != "SLPM_651.56":
                self.assertNotIn("display_256_dy_plus18", config)
                self.assertNotIn("display_256_horizontal_fix", config)

    def test_both_entries_transform_only_guarded_modes(self):
        cases = ((0, 255, 1, 479), (0, 239, 1, 479), (0, 223, 1, 447),
                 (0, 100, 0, 100), (1, 255, 1, 255))
        for hook, gs_address in zip(self.hooks, (0x12000080, 0x120000A0)):
            for magv, dh, expected_magv, expected_dh in cases:
                for dy in (0, 17, 49, 2047):
                    with self.subTest(hook=hex(hook[0]), magv=magv, dh=dh, dy=dy):
                        original = display(636, dy, 3, magv, 2559, dh)
                        output = run_helper(self.trial, self.va, hook, original, gs_address)
                        self.assertEqual(output, display(636, dy, 3, expected_magv, 2559, expected_dh))
                        previous = run_helper(self.previous_512, self.va, hook, original, gs_address)
                        if magv == 0 and dh == 255:
                            self.assertEqual(previous, display(636, dy, 3, 1, 2559, 511))
                        else:
                            self.assertEqual(output, previous)
                        if magv == 0 and dh in (223, 239):
                            self.assertEqual(output, run_helper(self.baseline, self.va, hook, original, gs_address))
                        elif magv != 0 or dh not in (223, 239, 255):
                            self.assertEqual(output, original)

    def test_measured_title_value_keeps_dy_17(self):
        observed = 0x000FF9FF0181127C
        output = run_helper(self.trial, self.va, self.hooks[1], observed, 0x120000A0)
        self.assertEqual(output, 0x001DF9FF0981127C)
        self.assertEqual(patch480p.decode_display_value(output), (636, 17, 3, 1, 2559, 479))
        self.assertEqual(run_helper(self.previous_512, self.va, self.hooks[1], observed, 0x120000A0),
                         0x001FF9FF0981127C)

    def test_dy_plus18_only_for_dh255_and_wraps_inside_11_bits(self):
        self.assertEqual(self.config["display_cave_size"], 0xF0)
        plus_words = struct.unpack(f"<{len(self.trial_dyplus18) // 4}I", self.trial_dyplus18)
        self.assertEqual(plus_words[25], patch480p.encode_r(
            0, patch480p.REG["t7"], patch480p.REG["t2"], 12, 0x3A
        ))
        self.assertEqual(plus_words[34], patch480p.encode_i(
            0x0E, patch480p.REG["t0"], patch480p.REG["t0"], 255
        ))
        self.assertEqual(35 + 1 + signed(plus_words[35] & 0xFFFF, 16), 43)
        self.assertEqual([text for text, _ in self.dy_listing[44:47]],
                         ["sd t7,0(t8)", "jr t9", "nop"])

        for hook, gs_address in zip(self.hooks, (0x12000080, 0x120000A0)):
            cases = ((0, 255), (0, 239), (0, 223), (0, 100), (1, 255))
            for magv, dh in cases:
                for dy in (0, 17, 2015, 2016, 2047):
                    with self.subTest(hook=hex(hook[0]), magv=magv, dh=dh, dy=dy):
                        original = display(636, dy, 3, magv, 2559, dh)
                        baseline, baseline_regs = run_helper(
                            self.trial, self.va, hook, original, gs_address, return_regs=True
                        )
                        corrected, corrected_regs = run_helper(
                            self.trial_dyplus18, self.va, hook, original, gs_address, return_regs=True
                        )
                        self.assertEqual(corrected_regs[patch480p.REG["t0"]],
                                         baseline_regs[patch480p.REG["t0"]])
                        self.assertEqual(corrected_regs[patch480p.REG["t2"]],
                                         baseline_regs[patch480p.REG["t2"]])
                        if magv == 0 and dh == 255:
                            self.assertEqual(
                                corrected,
                                display(636, (dy + 18) & 0x7FF, 3, 1, 2559, 479),
                            )
                        else:
                            self.assertEqual(corrected, baseline)

        observed = 0x000FF9FF0181127C
        self.assertEqual(
            run_helper(self.trial_dyplus18, self.va, self.hooks[1], observed, 0x120000A0),
            0x001DF9FF0982327C,
        )

    def test_horizontal_fix_is_guarded_and_preserves_other_fields(self):
        fixed, listing = patch480p.make_dynamic_display_helper(
            self.va, self.config["display_cave_size"], self.hooks,
            scale_256_rows=True, limit_256_to_480=True,
            adjust_256_dy_plus18=True, fix_256_horizontal=True,
        )
        self.assertEqual(len(fixed), 0xF0)
        self.assertEqual([item[0] for item in listing[57:60]],
                         ["sd t7,0(t8)", "jr t9", "nop"])
        words = struct.unpack("<60I", fixed)
        self.assertEqual(35 + 1 + signed(words[35] & 0xFFFF, 16), 56)
        for index in (5, 11, 15, 24, 59):
            self.assertEqual(words[index], 0)  # unchanged NOP delay slots
        self.assertEqual(words[36], patch480p.encode_i(
            0x0E, patch480p.REG["t0"], patch480p.REG["t0"], 255,
        ))  # DY gate delay slot restores t0

        observed = 0x000FF9FF0181127C
        expected = 0x001DF4FF08823138
        self.assertEqual(patch480p.decode_display_value(expected),
                         (312, 35, 1, 1, 1279, 479))
        for hook, gs_address in zip(self.hooks, (0x12000080, 0x120000A0)):
            with self.subTest(hook=hex(hook[0]), case="observed"):
                old = run_helper(self.trial_dyplus18, self.va, hook, observed, gs_address)
                new = run_helper(fixed, self.va, hook, observed, gs_address)
                self.assertEqual(old, 0x001DF9FF0982327C)
                self.assertEqual(new, expected)

            reserved = (0x1FF << 55) | (0x7 << 29)
            with self.subTest(hook=hex(hook[0]), case="reserved bits"):
                value = display(636, 17, 3, 0, 2559, 255) | reserved
                self.assertEqual(run_helper(fixed, self.va, hook, value, gs_address),
                                 expected | reserved)

            for dy in (0, 17, 2015, 2016, 2047):
                for dx, magh, dw in ((636, 3, 2559), (0, 0, 0), (4095, 15, 4095)):
                    value = display(dx, dy, magh, 0, dw, 255)
                    with self.subTest(hook=hex(hook[0]), dy=dy, dx=dx, magh=magh, dw=dw):
                        old, old_regs = run_helper(
                            self.trial_dyplus18, self.va, hook, value, gs_address,
                            return_regs=True,
                        )
                        new, new_regs = run_helper(
                            fixed, self.va, hook, value, gs_address, return_regs=True,
                        )
                        self.assertEqual(new, display(312, (dy + 18) & 0x7FF,
                                                      1, 1, 1279, 479))
                        self.assertEqual((new ^ old) & ~((0xFFF << 0) | (0xF << 23) |
                                                         (0xFFF << 32)), 0)
                        self.assertEqual(new_regs[patch480p.REG["t0"]],
                                         old_regs[patch480p.REG["t0"]])
                        self.assertEqual(new_regs[patch480p.REG["t2"]],
                                         old_regs[patch480p.REG["t2"]])

            for magv, dh in ((0, 223), (0, 239), (0, 100), (1, 255), (2, 255)):
                for dy in (17, 2047):
                    value = display(636, dy, 3, magv, 2559, dh)
                    with self.subTest(hook=hex(hook[0]), magv=magv, dh=dh, dy=dy):
                        self.assertEqual(
                            run_helper(fixed, self.va, hook, value, gs_address),
                            run_helper(self.trial_dyplus18, self.va, hook,
                                       value, gs_address),
                        )


if __name__ == "__main__":
    unittest.main()
