"""End-to-end regression for the 3rd Style BIOS-native 526 trial patch.

The original ISO is user-owned and is intentionally not stored in this
repository. Set IIDX3RD_REGRESSION_ISO to run this integration test locally.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import patch480p


EXPECTED_3RD_BIOS_NATIVE_ISO_SHA256 = (
    "32915DBB2572D90900F027B94DFC71D10E208E7461933EE7558825B47291C9EA"
)
SOURCE_ISO_ENV = "IIDX3RD_REGRESSION_ISO"


class ThirdStyleRegressionTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get(SOURCE_ISO_ENV),
        f"set {SOURCE_ISO_ENV} to a supported original 3rd Style ISO",
    )
    def test_bios_native_526_output_hash_is_stable(self):
        source = Path(os.environ[SOURCE_ISO_ENV]).resolve()
        with tempfile.TemporaryDirectory(
            prefix="iidx3rd-regression-",
            dir=Path(__file__).resolve().parent,
        ) as temp_dir:
            output = Path(temp_dir) / "3rd_bios_native_526_regression.iso"
            _source_hash, output_hash, _elf_hash, _helper_size, _listing, _code = (
                patch480p.build(source, output)
            )
            self.assertEqual(output_hash, EXPECTED_3RD_BIOS_NATIVE_ISO_SHA256)
            self.assertEqual(
                patch480p.sha256_file(output), EXPECTED_3RD_BIOS_NATIVE_ISO_SHA256
            )


if __name__ == "__main__":
    unittest.main()
