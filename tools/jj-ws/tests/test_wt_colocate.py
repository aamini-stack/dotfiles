from types import SimpleNamespace

import pytest
from jjws.lib.jj import Workspace
from jjws.wt import lifecycle


@pytest.fixture()
def repo(tmp_path):
    primary = tmp_path / "repo"
    (primary / ".jj" / "repo").mkdir(parents=True)
    (primary / ".git").mkdir()
    ws = tmp_path / "ws" / "feat"
    (ws / ".jj").mkdir(parents=True)
    return primary, ws


def _patch(monkeypatch, primary, items, commit="abc123"):
    monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
    monkeypatch.setattr(lifecycle, "workspaces", lambda cwd: items)
    monkeypatch.setattr(lifecycle, "commit_id", lambda revset, cwd: commit)
    runs = []
    monkeypatch.setattr(
        lifecycle.subprocess,
        "run",
        lambda *args, **kwargs: runs.append(args[0]) or SimpleNamespace(returncode=0),
    )
    return runs


class TestColocateWorkspaces:
    def test_registers_git_worktree(self, monkeypatch, repo):
        primary, ws = repo
        runs = _patch(
            monkeypatch,
            primary,
            [Workspace(name="default", root=primary), Workspace(name="feat", root=ws)],
        )

        converted = lifecycle.colocate_workspaces(primary)

        assert converted == [Workspace(name="feat", root=ws)]
        admin = primary / ".git" / "worktrees" / "feat"
        assert (admin / "gitdir").read_text() == f"{ws / '.git'}\n"
        assert (admin / "commondir").read_text() == "../..\n"
        assert (admin / "HEAD").read_text() == "abc123\n"
        assert (ws / ".git").read_text() == f"gitdir: {admin}\n"
        assert runs[0][:3] == ["git", "-C", str(primary)]
        assert "cat-file" in runs[0]
        assert runs[1][:3] == ["git", "-C", str(primary)]
        assert "repair" in runs[1]
        assert runs[2] == ["git", "-C", str(ws), "read-tree", "HEAD"]

    def test_skips_primary_and_already_colocated(self, monkeypatch, repo, tmp_path):
        primary, _ = repo
        colocated = tmp_path / "ws" / "old"
        (colocated / ".git").mkdir(parents=True)
        _patch(
            monkeypatch,
            primary,
            [
                Workspace(name="default", root=primary),
                Workspace(name="old", root=colocated),
            ],
        )

        assert lifecycle.colocate_workspaces(primary) == []

    def test_filters_by_name(self, monkeypatch, repo):
        primary, ws = repo
        _patch(monkeypatch, primary, [Workspace(name="feat", root=ws)])

        converted = lifecycle.colocate_workspaces(primary, "feat")

        assert converted == [Workspace(name="feat", root=ws)]

    def test_unknown_name_errors(self, monkeypatch, repo):
        primary, ws = repo
        _patch(monkeypatch, primary, [Workspace(name="feat", root=ws)])

        with pytest.raises(lifecycle.WtError, match="ghost"):
            lifecycle.colocate_workspaces(primary, "ghost")

    def test_errors_when_primary_not_colocated(self, monkeypatch, tmp_path):
        primary = tmp_path / "repo"
        (primary / ".jj" / "repo").mkdir(parents=True)
        _patch(monkeypatch, primary, [])

        with pytest.raises(lifecycle.WtError, match="not colocated"):
            lifecycle.colocate_workspaces(primary)

    def test_errors_when_commit_missing_from_git(self, monkeypatch, repo):
        primary, ws = repo
        monkeypatch.setattr(lifecycle, "primary_root", lambda cwd: primary)
        monkeypatch.setattr(
            lifecycle, "workspaces", lambda cwd: [Workspace(name="feat", root=ws)]
        )
        monkeypatch.setattr(lifecycle, "commit_id", lambda revset, cwd: "abc123")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=1),
        )

        with pytest.raises(lifecycle.WtError, match="object store"):
            lifecycle.colocate_workspaces(primary)
        assert not (ws / ".git").exists()
