import unittest
from unittest.mock import Mock, patch

import automtu.__main__ as entry


class TestMain(unittest.TestCase):
    def test_main_calls_parser_and_core(self) -> None:
        fake_args = object()
        fake_parser = Mock()
        fake_parser.parse_args.return_value = fake_args

        with (
            patch("automtu.__main__.build_parser", return_value=fake_parser) as p_build,
            patch("automtu.__main__.run_automtu", return_value=0) as p_run,
        ):
            rc = entry.main()

        self.assertEqual(rc, 0)
        p_build.assert_called_once_with()
        fake_parser.parse_args.assert_called_once_with()
        p_run.assert_called_once_with(fake_args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
