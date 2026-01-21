from __future__ import annotations

from .cli import build_parser
from .core import run_automtu


def main() -> int:
    args = build_parser().parse_args()
    return run_automtu(args)


if __name__ == "__main__":
    raise SystemExit(main())
