"""End-to-end regression for the publicly released 3rd Style v1.0 patch.

The original ISO is user-owned and is intentionally not stored in this
repository. Set IIDX3RD_REGRESSION_ISO to run this integration test locally.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import patch480p


EXPECTED_3RD_V1_0_ISO_SHA256 = (
    "937A6109F60B4E17A9C88CD5F68B8E0F0886F326948958E35EA20BB7CCB6406B"
)
SOURCE_ISO_ENV = "IIDX3RD_REGRESSION_ISO"


class ThirdStyleRegressionTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get(SOURCE_ISO_ENV),
        f"set {SOURCE_ISO_ENV} to a supported original 3rd Style ISO",
    )
    def test_public_v1_0_output_hash_is_unchanged(self):
        source = Path(os.environ[SOURCE_ISO_ENV]).resolve()
        with tempfile.TemporaryDirectory(
            prefix="iidx3rd-regression-",
            dir=Path(__file__).resolve().parent,
        ) as temp_dir:
            output = Path(temp_dir) / "3rd_v1.0_regression.iso"
            _source_hash, output_hash, _elf_hash, _helper_size, _listing, _code, _table = (
                patch480p.build(source, output, "v1.0")
            )
            self.assertEqual(output_hash, EXPECTED_3RD_V1_0_ISO_SHA256)
            self.assertEqual(
                patch480p.sha256_file(output), EXPECTED_3RD_V1_0_ISO_SHA256
            )


if __name__ == "__main__":
    unittest.main()
