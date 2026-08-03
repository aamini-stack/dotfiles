from cli.jj import Workspace
from cli.wt import lifecycle, main


def test_resolve_workspace_looks_up_by_name(monkeypatch, tmp_path):
    primary = tmp_path / "repo"
    target = Workspace("feat", tmp_path / "ws" / "feat")
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle, "workspace", lambda cwd, name: target)

    assert lifecycle.resolve_workspace(tmp_path, "feat") == target


def test_pick_workspace_returns_selected(monkeypatch, tmp_path):
    current = Workspace("default", tmp_path / "repo")
    feat = Workspace("feat", tmp_path / "ws" / "feat")
    monkeypatch.setattr(lifecycle, "current_workspace", lambda cwd: current)
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: current.root)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [current, feat])
    seen = {}

    def fake_select(lines):
        seen["lines"] = lines
        return ("enter", lines[1])

    picked = lifecycle.pick_workspace(tmp_path, select=fake_select)

    assert picked == feat
    assert seen["lines"] == [
        f"* default\t{current.root}",
        f"  feat\t{feat.root}",
    ]


def test_pick_workspace_cancel_returns_none(monkeypatch, tmp_path):
    current = Workspace("default", tmp_path / "repo")
    monkeypatch.setattr(lifecycle, "current_workspace", lambda cwd: current)
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: current.root)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: [current])

    assert (
        lifecycle.pick_workspace(tmp_path, select=lambda lines: ("esc", None)) is None
    )


def run_wt(monkeypatch, argv, env=None):
    monkeypatch.setattr("sys.argv", ["wt", *argv])
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)
    return main.main()


def test_switch_named_emits_existing_root(monkeypatch, tmp_path, capsys):
    target = Workspace("feat", tmp_path / "ws" / "feat")
    monkeypatch.setattr(main, "resolve_workspace", lambda cwd, name: target)

    assert run_wt(monkeypatch, ["switch", "feat"]) == 0
    assert capsys.readouterr().out.strip() == str(target.root)


def test_switch_create_creates_and_emits(monkeypatch, tmp_path, capsys):
    target = Workspace("feat", tmp_path / "ws" / "feat")
    seen = {}
    monkeypatch.setattr(
        main,
        "create_workspace",
        lambda cwd, name, revision, force=False: (
            seen.update(name=name, revision=revision, force=force) or target
        ),
    )

    assert run_wt(monkeypatch, ["switch", "-c", "feat", "-r", "trunk()"]) == 0
    assert seen == {"name": "feat", "revision": "trunk()", "force": False}
    assert capsys.readouterr().out.strip() == str(target.root)


def test_switch_create_forwards_force(monkeypatch, tmp_path, capsys):
    target = Workspace("feat", tmp_path / "ws" / "feat")
    seen = {}
    monkeypatch.setattr(
        main,
        "create_workspace",
        lambda cwd, name, revision, force=False: seen.update(force=force) or target,
    )

    assert run_wt(monkeypatch, ["switch", "-c", "feat", "--force"]) == 0
    assert seen == {"force": True}


def test_switch_create_requires_name(monkeypatch, capsys):
    assert run_wt(monkeypatch, ["switch", "--create"]) == 1
    assert "requires a name" in capsys.readouterr().err


def test_switch_revision_without_create_fails(monkeypatch, capsys):
    assert run_wt(monkeypatch, ["switch", "feat", "-r", "trunk()"]) == 1
    assert "--revision only applies with --create" in capsys.readouterr().err


def test_switch_no_args_picks_with_fzf(monkeypatch, tmp_path, capsys):
    target = Workspace("feat", tmp_path / "ws" / "feat")
    monkeypatch.setattr(main, "pick_workspace", lambda cwd: target)

    assert run_wt(monkeypatch, ["switch"]) == 0
    assert capsys.readouterr().out.strip() == str(target.root)


def test_switch_pick_cancelled_prints_nothing(monkeypatch, capsys):
    monkeypatch.setattr(main, "pick_workspace", lambda cwd: None)

    assert run_wt(monkeypatch, ["switch"]) == 0
    assert capsys.readouterr().out == ""


def test_switch_writes_result_file_when_set(monkeypatch, tmp_path, capsys):
    target = Workspace("feat", tmp_path / "ws" / "feat")
    result_file = tmp_path / "result"
    monkeypatch.setattr(main, "resolve_workspace", lambda cwd, name: target)

    assert (
        run_wt(
            monkeypatch, ["switch", "feat"], env={"WT_RESULT_FILE": str(result_file)}
        )
        == 0
    )
    assert result_file.read_text() == str(target.root)
    assert capsys.readouterr().out == ""


def test_switch_create_emits_destination_even_when_hooks_fail(
    monkeypatch, tmp_path, capsys
):
    target = Workspace("feat", tmp_path / "ws" / "feat")
    result_file = tmp_path / "result"

    def failing_create(cwd, name, revision, force=False):
        raise lifecycle.CreateHookError(target, "post-create.bootstrap failed")

    monkeypatch.setattr(main, "create_workspace", failing_create)

    assert (
        run_wt(
            monkeypatch,
            ["switch", "-c", "feat"],
            env={"WT_RESULT_FILE": str(result_file)},
        )
        == 1
    )
    assert result_file.read_text() == str(target.root)
    assert "post-create.bootstrap failed" in capsys.readouterr().err
