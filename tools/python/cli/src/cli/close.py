"""Close the herdr workspace for a removed jj workspace.

Invoked by the workspace tool's post-remove hook with the repo and workspace
name. A missing herdr workspace is not an error: the hook runs for every
removal, including workspaces that were never opened in herdr.
"""

import argparse
import sys

from . import guard
from .herdr import HerdrError, close_for_jj


def close_workspace(repo: str, name: str) -> int:
    existing, workspaces = close_for_jj(repo, name)
    live_ids = {w["workspace_id"] for w in workspaces}

    if existing is not None:
        live_ids.discard(existing["workspace_id"])
        try:
            guard.disarm(existing["workspace_id"])
        except OSError as error:
            print(f"herdr-ws close: cd-guard disarm failed: {error}", file=sys.stderr)

    try:
        guard.prune(live_ids)
    except OSError as error:
        print(f"herdr-ws close: cd-guard prune failed: {error}", file=sys.stderr)
    return 0


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "close", help="close the herdr workspace for a removed jj workspace"
    )
    parser.add_argument("--repo", required=True, help="repo directory name")
    parser.add_argument("--name", required=True, help="jj workspace name")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    try:
        return close_workspace(args.repo, args.name)
    except HerdrError as error:
        print(f"herdr-ws close: {error}", file=sys.stderr)
        return 1
