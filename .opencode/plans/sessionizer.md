# herdr sessionizer: consolidate into herdr-jj + opencode session migration

## Context & key findings

- Prime's tmux-sessionizer: bash script; fzf over existing sessions + project dirs; session ≡ (dir, sanitized name); create-if-missing + `switch-client`. Bound to `ctrl-f`.
- We already had two herdr equivalents: the vendored `sessionizer` plugin (`prefix+f`) and `aamini.jj` pick (`prefix+a`). Decision: **port the useful part (cross-project picker) into `aamini.jj`, delete the vendored plugin.**
- The vendored sessionizer was nearly useless here: its roots `~/Projects`, `~/Workspace` **don't exist on this machine**, its existing-workspaces screen duplicates herdr's built-in `prefix+w`, its layout spawns `lazygit` (we use jj/jjui), and `prefix+up` (worktree-open) is git-branch-centric, redundant with `prefix+a` / `prefix+shift+a` / `wt switch -c`.
- **Key discovery:** opencode sessions are **repo-scoped, not directory-scoped**. All jj workspaces of a repo share one `projectId` (verified: `opencode session list` run inside `~/.herdr/workspaces/dotfiles/ryu-gh-stacks` lists sessions started in `~/dotfiles`). So "moving a session to a new worktree" needs **no export/import** — just create the jj workspace and launch `opencode --session <id> --fork` there. `--fork` because the original pane still has the session open; the old session stays intact, the new worktree gets an independent copy with full history.

## Build

### 1. `aamini.jj.migrate` action (bound to `prefix+m`) — the one-command migration

Popup flow (new `tools/python/cli/src/cli/plugin/migrate.py`, subcommand `migrate-popup`):

1. `cwd` from `resolve_context(env)`; `primary = primary_root(cwd)` (fail cleanly outside a jj repo).
2. Latest session: run `opencode session list -n 1 --format json` with `cwd=cwd`, parse `[0]["id"]`. If none: warn and continue with plain `opencode` as the agent command.
3. Prompt for workspace name (`input_fn`, like wizard.py). No rev picker by design — the workspace always branches at the current rev.
4. `create_workspace(cwd, name, env=env)` — `revision` defaults to `@` (wt/lifecycle.py:56).
5. `open_workspace(created.root, primary, created.name, agent_command=f"opencode --session {sid} --fork")`.
6. `reporter.ensure(env)` like wizard does.

Supporting change in `src/cli/open.py`: add `agent_command: str | None = None` to `open_workspace()`; in the new-workspace branch run `agent_command or "opencode"` in the right pane (ignored when focusing an existing workspace).

### 2. `aamini.jj.projects` action (bound to `prefix+f`) — sessionizer replacement

New `tools/python/cli/src/cli/plugin/projects.py`, subcommand `projects-popup`:

- Roots: read `[projects]` table from `~/.config/wt/config.toml` via `tomllib` directly (`roots`, default `["~/apps", "~/toolkit", "~/tools", "~/dotfiles"]` — dirs that actually exist here). A root counts itself if it's a repo, plus immediate children (depth 1) containing `.jj` or `.git` (file or dir).
- Rows (tab-delimited): existing herdr workspaces as `open\t<label>\t<workspace_id>`; discovered project dirs (deduped against workspace `cwd`s) as `proj\t<name>\t<path>`. Preview: dir listing / `jj log` fallback.
- Selection: `open` → `focus_workspace(id)`; `proj` → jj repo: `open_workspace(path, primary_root(path), current_workspace(path).name)`; git-only: `open_workspace(path)` (bootstrap + opencode layout, consistent with everything else).

### 3. Wiring

- `src/cli/plugin/actions.py`: add `migrate()` → `_open_pane("migrate-popup", env)` and `projects()` → `_open_pane("projects-popup", env, require_repo=False)`; `_open_pane` gains `require_repo: bool = True` (projects must work outside jj repos — currently hard-fails on `primary_root`).
- `src/cli/plugin/main.py`: import + register `migrate`, `projects` modules.
- `tools/herdr-jj/herdr-plugin.toml`: add `[[actions]] migrate` (contexts `["workspace"]`), `[[actions]] projects` (contexts `["workspace", "global"]`), `[[panes]] migrate-popup` and `[[panes]] projects-popup` (placement `popup`), mirroring the pick/picker pattern.
- `.config/herdr/config.toml`: `prefix+f` → `aamini.jj.projects` ("open project"); add `prefix+m` → `aamini.jj.migrate`; delete the `sessionizer.worktree-open` (`prefix+up`) binding.
- `.config/herdr/plugins.json`: remove the sessionizer entry.
- Delete `.config/herdr/plugins/github/sessionizer-66e03d1ff740/` and `.config/herdr/plugins/config/sessionizer/`.

### 4. Tests (`tools/python/cli/tests/`)

Follow existing patterns (mock at the subprocess boundary):

- `open_workspace` with `agent_command` override (used on create, ignored on focus-existing).
- `migrate`: mock `opencode session list`, `input_fn`, `create_workspace`, `open_workspace`; assert `agent_command` is `opencode --session <id> --fork` and no revision is passed (defaults to `@`); no-session fallback path.
- `projects`: tmp roots with fake `.jj`/`.git` dirs; discovery, dedupe against existing workspaces, focus vs open routing.

## Verification

1. `mise //tools/python:test` and the lint/format tasks in `tools/python/mise.toml` (ruff).
2. Restart herdr (or reload) so the manifest/keybind changes load; confirm no plugin errors and `prefix+a` / `prefix+shift+a` still work.
3. Migrate e2e: in `~/dotfiles` (has opencode sessions) `prefix+m` → name `test-migrate` → assert workspace `ws-dotfiles-test-migrate` opens at `@`, right pane shows the forked opencode session with full history; `jj workspace list` shows the new workspace; original session untouched. Clean up with `wt rm test-migrate`.
4. Projects e2e: `prefix+f` from any workspace → popup lists open workspaces + dirs under the configured roots → pick one → opens with bootstrap+opencode layout.
5. `prefix+up` is unbound; sessionizer dirs/plugins.json entry gone.

## Notes

- herdr's native worktree UI is unaffected: the create-worktree button, `prefix+shift+g`, and `[worktrees] directory` are herdr core, not the sessionizer plugin. The existing `worktree.created → adopt` event (plugin/adopt.py) keeps converting UI-created git worktrees into jj workspaces in place, and the new actions attach native worktree provenance via `_worktree_open` so their workspaces nest under the repo in the same UI.
- For the "unrelated change higher up the tree" case where you *don't* need both checkouts simultaneously, plain `jj new <rev>` in the same directory is the zero-tooling answer — jj auto-snapshots, the opencode session never moves. The migrate action is for when you want both alive (review session stays, refactor happens elsewhere).
- Rev picking was deliberately dropped from migrate — it always branches at `@`. For an explicit revision, `wt switch -c <name> -r <rev>` remains available.
- Known limitation: migration across *different repos* (separate clones, different `projectId`) isn't covered — that would need `opencode export`/`import`; out of scope since `aamini.jj` workspaces are same-repo by construction.
