"""herdr-jj: aamini.jj plugin command dispatcher."""

import argparse

from . import actions, picker, remove, reporter, wizard


def main() -> int:
    parser = argparse.ArgumentParser(prog="herdr-jj", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    actions.add_parser(subparsers)
    wizard.add_parser(subparsers)
    remove.add_parser(subparsers)
    picker.add_parser(subparsers)
    reporter.add_parser(subparsers)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
