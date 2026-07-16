#!/usr/bin/env python3
import argparse
import json
import os
import socket
import subprocess
import sys
import hashlib
import time


def hash_port(s: str) -> int:
    """Deterministic port in 10000-19999 for a string."""
    h = hashlib.sha256(s.encode()).hexdigest()
    return 10000 + (int(h, 16) % 10000)


def load_layout(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def substitute(obj, replacements: dict):
    if isinstance(obj, str):
        for k, v in replacements.items():
            obj = obj.replace(k, str(v))
        return obj
    if isinstance(obj, list):
        return [substitute(item, replacements) for item in obj]
    if isinstance(obj, dict):
        return {k: substitute(v, replacements) for k, v in obj.items()}
    return obj


def send_request(sock_path: str, request: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(sock_path)
        s.send((json.dumps(request) + "\n").encode())
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            try:
                return json.loads(data.decode())
            except json.JSONDecodeError:
                continue
    raise RuntimeError("no response from herdr socket")


def herdr_cli(*args) -> dict:
    herdr_bin = os.environ.get("HERDR_BIN_PATH", "herdr")
    result = subprocess.run(
        [herdr_bin] + list(args),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def herdr_run(*args):
    herdr_bin = os.environ.get("HERDR_BIN_PATH", "herdr")
    subprocess.run([herdr_bin] + list(args), check=True)


def apply_layout(
    sock_path: str, tab_id: str, label: str, focus: bool, root: dict
) -> dict:
    request = {
        "id": f"layout_apply_{label}",
        "method": "layout.apply",
        "params": {
            "tab_id": tab_id,
            "tab_label": label,
            "focus": focus,
            "root": root,
        },
    }
    return send_request(sock_path, request)


def focus_tab(sock_path: str, tab_id: str):
    request = {
        "id": "tab_focus",
        "method": "tab.focus",
        "params": {"tab_id": tab_id},
    }
    response = send_request(sock_path, request)
    if response.get("error"):
        raise RuntimeError(f"tab.focus failed: {response['error']}")


def extract_cmd(command_arr):
    if len(command_arr) >= 3 and command_arr[0] == "sh" and command_arr[1] == "-c":
        return command_arr[2]
    return " ".join(command_arr)


def get_socket_path() -> str:
    if "HERDR_SOCKET_PATH" in os.environ:
        return os.environ["HERDR_SOCKET_PATH"]
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    default = os.path.join(config_home, "herdr", "herdr.sock")
    if os.path.exists(default):
        return default
    return ""


def get_workspace_root_pane(ws_id: str) -> str | None:
    tabs = herdr_cli("tab", "list", "--workspace", ws_id)["result"]["tabs"]
    if not tabs:
        return None
    first_tab_id = tabs[0]["tab_id"]
    panes = herdr_cli("pane", "list", "--workspace", ws_id)["result"]["panes"]
    for pane in panes:
        if pane.get("tab_id") == first_tab_id:
            return pane["pane_id"]
    return None


def find_workspace_by_path(worktree_path: str) -> tuple[str | None, str | None]:
    """Return (workspace_id, active_tab_id) for a worktree path."""
    worktree_path = os.path.realpath(worktree_path)
    for ws in herdr_cli("workspace", "list")["result"]["workspaces"]:
        wt = ws.get("worktree")
        if wt and os.path.realpath(wt.get("checkout_path", "")) == worktree_path:
            return ws["workspace_id"], ws.get("active_tab_id")
    for ws in herdr_cli("workspace", "list")["result"]["workspaces"]:
        root_pane = get_workspace_root_pane(ws["workspace_id"])
        if not root_pane:
            continue
        pane = herdr_cli("pane", "get", root_pane)["result"]["pane"]
        cwd = os.path.realpath(pane.get("cwd") or pane.get("foreground_cwd") or "")
        if cwd == worktree_path:
            return ws["workspace_id"], ws.get("active_tab_id")
    return None, None


def apply_worktree_layout(
    workspace_id: str, initial_tab_id: str, worktree_path: str, branch: str
):
    plugin_root = os.environ.get(
        "HERDR_PLUGIN_ROOT", os.path.dirname(os.path.abspath(__file__))
    )
    layout_path = os.path.join(plugin_root, "layout.json")
    layout = load_layout(layout_path)

    test_port = hash_port(f"test-ui-{branch}")
    replacements = {
        "{WORKTREE_PATH}": worktree_path,
        "{WT_TEST_PORT}": test_port,
    }
    layout = substitute(layout, replacements)

    tabs = layout.get("tabs", [])
    if not tabs:
        print("layout has no tabs", file=sys.stderr)
        sys.exit(1)

    socket_path = get_socket_path()
    if not socket_path:
        print("herdr socket path not found", file=sys.stderr)
        sys.exit(1)

    first_tab_id = None

    for i, tab in enumerate(tabs):
        if tab.get("replace_initial"):
            response = apply_layout(
                socket_path,
                initial_tab_id,
                tab["label"],
                focus=(i == 0),
                root=tab["root"],
            )
            if response.get("error"):
                print(
                    f"layout.apply failed for {tab['label']}: {response['error']}",
                    file=sys.stderr,
                )
                sys.exit(1)
            first_tab_id = response["result"]["layout"]["tab_id"]
        else:
            tab_result = herdr_cli(
                "tab",
                "create",
                "--workspace",
                workspace_id,
                "--label",
                tab["label"],
                "--no-focus",
            )
            left_pane_id = tab_result["result"]["root_pane"]["pane_id"]
            time.sleep(0.5)

            split_result = herdr_cli(
                "pane", "split", left_pane_id, "--direction", "right", "--no-focus"
            )
            right_pane_id = split_result["result"]["pane"]["pane_id"]

            time.sleep(0.1)

            left_pane = tab["root"]["first"]
            right_pane = tab["root"]["second"]

            left_label = left_pane.get("label", "")
            right_label = right_pane.get("label", "")
            if left_label:
                herdr_run("pane", "rename", left_pane_id, left_label)
            if right_label:
                herdr_run("pane", "rename", right_pane_id, right_label)

            left_cmd = extract_cmd(left_pane["command"])
            right_cmd = extract_cmd(right_pane["command"])
            herdr_run("pane", "run", left_pane_id, left_cmd)
            herdr_run("pane", "run", right_pane_id, right_cmd)

    if first_tab_id:
        focus_tab(socket_path, first_tab_id)

    print("layout applied")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-id")
    parser.add_argument("--active-tab-id")
    parser.add_argument("--worktree-path")
    parser.add_argument("--branch", default="")
    args = parser.parse_args()

    if args.workspace_id and args.active_tab_id and args.worktree_path:
        workspace_id = args.workspace_id
        initial_tab_id = args.active_tab_id
        worktree_path = args.worktree_path
        branch = args.branch
    elif args.worktree_path:
        worktree_path = args.worktree_path
        branch = args.branch
        workspace_id, initial_tab_id = find_workspace_by_path(worktree_path)
    else:
        event_json = os.environ.get("HERDR_PLUGIN_EVENT_JSON", "{}")
        try:
            event = json.loads(event_json)
        except json.JSONDecodeError as e:
            print(f"invalid event json: {e}", file=sys.stderr)
            sys.exit(1)

        payload = event.get("data") if isinstance(event, dict) else event
        if not isinstance(payload, dict):
            payload = event
        workspace = payload.get("workspace") if isinstance(payload, dict) else {}
        worktree = payload.get("worktree") if isinstance(payload, dict) else {}

        if not isinstance(workspace, dict) or not isinstance(worktree, dict):
            print("event missing workspace/worktree", file=sys.stderr)
            sys.exit(1)

        workspace_id = workspace.get("workspace_id")
        initial_tab_id = workspace.get("active_tab_id")
        worktree_path = worktree.get("path")
        branch = worktree.get("branch") or ""

    if not workspace_id or not initial_tab_id:
        if not worktree_path:
            print("missing workspace info or worktree path", file=sys.stderr)
            sys.exit(1)
        workspace_id, initial_tab_id = find_workspace_by_path(worktree_path)
        if not workspace_id or not initial_tab_id:
            print(
                f"could not find herdr workspace for {worktree_path}", file=sys.stderr
            )
            sys.exit(1)

    apply_worktree_layout(workspace_id, initial_tab_id, worktree_path, branch)


if __name__ == "__main__":
    main()
