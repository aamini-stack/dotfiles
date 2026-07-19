"""herdr-ws: manage herdr workspaces for jj workspaces."""

import argparse

from . import close, open


def main() -> int:
    parser = argparse.ArgumentParser(prog="herdr-ws", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    open.add_parser(subparsers)
    close.add_parser(subparsers)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
