"""Version smoke test."""

import unittest

from mediacurator import __version__


class VersionTests(unittest.TestCase):
    def test_version(self) -> None:
        self.assertTrue(__version__)


if __name__ == "__main__":
    unittest.main()
