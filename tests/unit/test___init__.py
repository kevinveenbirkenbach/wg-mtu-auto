import unittest

import automtu


class TestInit(unittest.TestCase):
    def test_version_is_exposed(self) -> None:
        self.assertTrue(hasattr(automtu, "__version__"))
        self.assertIsInstance(automtu.__version__, str)
        self.assertRegex(automtu.__version__, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
