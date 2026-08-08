# jj ⇄ worktrunk interop

## Goal

Use real worktrunk (`wt`, max-sixty/worktrunk — Aria loves its TUI) for
list/switch/remove over jj workspaces, while workspace **creation stays
jj-first** (herdr-jj wizard / custom `wt switch -c`). Requires the jj fork
(sjawhar/jj, `sami` branch) which auto-registers a Git worktree for every
colocated `jj workspace add`.

## Key investigation findings (why the design is what it is)

- Worktrunk's `pre-start` hook runs **after** it creates the git worktree, and
  the fork's `jj workspace add` refuses to adopt an existing directory (it
  creates its own worktree; `--no-colocate` hits the stock "not an empty
  directory" check). `pre-switch` doesn't help either: creating jj-first makes
  `wt switch -c` abort with "Branch already exists". **Conclusion: `wt switch
  -c` can never be the create path without a fork "adopt" mode — creation is
  jj-first, permanently.**
- The fork previously created worktrees with **detached HEAD** → worktrunk
  listed them as branch `-` and couldn't switch to them. Verified in a
  sandbox: once a worktree has a real branch, `wt list` / `wt switch` / `wt
  remove` all work against jj-created workspaces.
- `git worktree add --orphan -B <branch>` refuses an **existing** branch even
  with `-B`, so stale plumbing branches must be deleted before re-adding.
- Worktrunk requires `worktree-path` in **user** config; it warns-and-ignores
  it in project config.
- Worktrunk hook template variables are shell-escaped automatically; adding
  quotes around `{{ ... }}` breaks them.
- `cargo test -p jj-lib` is broken on the sami branch independent of this work
  (tokio feature-gating from the #8719 merge); use `--all-features`.

## Done

### 1. jj fork: attached plumbing branches (`~/apps/jj`, branch `sami-worktree-branch`, commit `d75cbf628`)

Secondary colocated workspaces (`.git` is a gitfile) now keep HEAD **attached**
to `refs/heads/jj-worktree-<workspace-name>`, moved to the working-copy parent
on every `reset_head_at_workspace`. Details:

- `lib/src/git.rs`
  - `WORKTREE_BRANCH_PREFIX` / `worktree_branch_name()` helper.
  - `parse_git_ref()` ignores `refs/heads/jj-worktree-*` → plumbing branches
    are never imported as bookmarks, exported, or pushed.
  - `update_git_head_attached()`: moves the branch (`PreviousValue::Any` — the
    branch may not exist yet for hand-registered worktrees) and points HEAD at
    it symbolically.
- `cli/src/commands/workspace/add.rs` — deletes a stale plumbing branch before
  `git worktree add` (orphan `-B` limitation above).
- `cli/src/commands/workspace/forget.rs` — `--cleanup` also deletes the
  plumbing branch.
- `cli/tests/test_git_colocated.rs` — updated
  `test_colocated_workspace_independent_heads` to attached-HEAD semantics;
  new `test_colocated_workspace_head_attached_to_plumbing_branch` covers
  attachment, no-bookmark-pollution, and forget-cleanup.
- Verified: 52 colocated + 60 workspace + 268 git CLI tests pass;
  `cargo test -p jj-lib --all-features git::` 104 pass. Sandbox end-to-end:
  create → attach → `wt list`/`wt switch` → `wt remove` → jj workspace
  forgotten; external `git commit` in a worktree imports correctly.

**Caveat:** attachment is *lazy* — `jj workspace add` leaves HEAD on an unborn
orphan branch; the first jj command run inside the new workspace attaches it
(matches the fork's documented lazy Git-view refresh). Anything that runs jj in
the workspace (hooks, opening it) attaches immediately.

### 2. Worktrunk user config (`dotfiles/.config/worktrunk/config.toml`, stowed to `~/.config/worktrunk/`)

```toml
worktree-path = "~/.herdr/workspaces/{{ repo }}/{{ branch | replace('jj-worktree-', '') | sanitize }}"

[post-remove]
jj-forget = "b={{ branch }}; case $b in jj-worktree-*) jj -R {{ primary_worktree_path }} workspace forget ${b#jj-worktree-} || true ;; esac"
```

- `replace` strips the plumbing prefix so worktrunk's expected path matches
  where herdr-jj/custom wt actually create workspaces (no mismatch warnings).
- `post-remove` makes real `wt remove jj-worktree-feat` also forget the jj
  workspace. Verified end-to-end in the sandbox.

### 3. herdr-jj wizard: switch-first creation (`dotfiles/tools/python/cli`)

`prefix+shift+A` no longer blocks the popup on bootstrap/hooks, and hook
failure no longer prevents the switch:

- `wt/lifecycle.py` — `create_workspace(..., run_post_create=False)` skips
  hooks; new `run_configured_phase()`.
- `wt/main.py` — `wt hook <phase>` runs a whole phase (e.g. `wt hook post-create`).
- `open.py` — `open_workspace(..., run_setup=True)` composes the left-pane
  command: `wt hook post-create && mise run bootstrap`.
- `plugin/wizard.py` — creates hookless, opens/focuses immediately, setup runs
  visibly in the pane.
- `jj.py` — `forget_workspace` also deletes the `jj-worktree-<name>` plumbing
  branch (custom `wt rm` trashes the dir before forgetting, so the fork's
  `--cleanup` can't see it).
- 166 tests pass (incl. e2e). The uv tool `cli` is editable-installed, so all
  of this is live.

## Remaining work

1. **Land the fork change**: push `sami-worktree-branch` to sjawhar/jj (or PR
   onto `sami`), cut a release via the repo's sami-build workflow
   (tag format `v0.43.0-sami.YYYYMMDD-HHMMSS`), then bump the pin in
   `dotfiles/.config/mise/config.toml` (`github:sjawhar/jj`).
2. **Decide the `wt` binary story**: mise can install worktrunk
   (`github:max-sixty/worktrunk`, already in `mise.lock` but not in config),
   whose binary is also named `wt`. It conflicts with the custom uv-tool `wt`
   at `~/.local/bin/wt` (which herdr-jj and the zsh wrapper use). Options:
   rename one, or shim worktrunk as e.g. `wtr`. Until resolved, real worktrunk
   is only at `/tmp/opencode/worktrunk-aarch64-unknown-linux-musl/wt` (throwaway).
3. **Shell integration for the TUI**: real `wt switch` prints "cannot change
   directory — shell integration not installed". `wt config shell install zsh`
   fixes cd-on-switch but will fight the custom zsh `wt` wrapper (which captures
   custom wt's printed path). Resolve together with (2).
4. **`jj workspace rename`** does not rename the plumbing branch — worktrunk
   would show the stale name. Follow-up fork change.
5. **Re-verify herdr-jj remove flow** against the released jj: `wt rm` →
   prune + branch delete (done in jj.py, tested with mocks only).
6. Sandbox leftovers to delete: `/tmp/opencode/wtexp`, `/tmp/opencode/dbg`,
   `/tmp/opencode/worktrunk-*`.

## Suggested skills

- `diagnosing-bugs` — if the fork change shows unexpected behavior after release.
- `research` — checking worktrunk upstream for native vcs-agnostic/jj support
  (max-sixty/worktrunk issues) before investing more in the fork.
