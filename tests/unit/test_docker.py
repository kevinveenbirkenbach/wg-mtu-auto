import unittest
from unittest.mock import patch

import automtu.docker as docker


class TestDocker(unittest.TestCase):
    def test_detect_docker_ifaces_explicit_dedup_and_drop_unknown(self) -> None:
        # explicit args are repeatable and/or comma-separated
        args = ["docker0,br-abc,unknown0", "br-abc,docker0"]

        def fake_iface_exists(name: str) -> bool:
            return name in {"docker0", "br-abc"}  # unknown0 does not exist

        with patch("automtu.docker.iface_exists", side_effect=fake_iface_exists):
            got = docker.detect_docker_ifaces(args, include_user_bridges=True)

        # preserve order, de-dup, drop unknown
        self.assertEqual(got, ["docker0", "br-abc"])

    def test_detect_docker_ifaces_auto_detect_docker0_only(self) -> None:
        # no explicit args -> auto detect
        def fake_iface_exists(name: str) -> bool:
            return name == "docker0"

        with patch("automtu.docker.iface_exists", side_effect=fake_iface_exists):
            got = docker.detect_docker_ifaces(None, include_user_bridges=False)

        self.assertEqual(got, ["docker0"])

    def test_detect_docker_ifaces_auto_detect_includes_user_bridges(self) -> None:
        # docker0 exists + br-* exists in list_ifaces -> included if include_user_bridges=True
        def fake_iface_exists(name: str) -> bool:
            return name in {"docker0", "br-abc"}  # br-abc exists, br-nope does not

        with (
            patch("automtu.docker.iface_exists", side_effect=fake_iface_exists),
            patch(
                "automtu.docker.list_ifaces",
                return_value=["lo", "eth0", "br-abc", "br-nope", "wg0"],
            ),
        ):
            got = docker.detect_docker_ifaces(None, include_user_bridges=True)

        self.assertEqual(got, ["docker0", "br-abc"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
