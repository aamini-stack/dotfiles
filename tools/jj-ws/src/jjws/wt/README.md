# wt

`wt` creates and removes jj workspaces, copies ignored files, and runs project
lifecycle hooks. It does not know about herdr; herdr-jj wraps it with workspace
focus, panes, and status reporting.

## Core commands

| Task | Command | Notes |
| --- | --- | --- |
| Switch to a workspace | `wt switch feat` | Prints the path; the zsh wrapper cds into it |
| Pick a workspace with fzf | `wt switch` | No name opens an interactive picker |
| Create and switch | `wt switch -c feat` | Bases the workspace on `@` and runs start and switch hooks |
| Create from another revision | `wt switch -c feat -r 'trunk()'` | Accepts any jj revset |
| List workspaces | `wt ls` | Shows names, paths, and the current workspace |
| Remove by name | `wt rm feat` | Confirms, runs `pre-remove`, forgets, removes the directory, then runs `post-remove` |
| Remove the current workspace | `wt rm` | The primary workspace is never removable |
| Remove without a prompt | `wt rm feat --yes` | Intended for trusted integrations such as herdr-jj |
| Run a named hook | `wt hook copy-envs` | Searches all supported lifecycle phases |
| Run a whole hook phase | `wt hook pre-start` | Runs every hook in the phase, stopping at the first failure |
| Copy ignored files | `wt copy-ignored` | Copies from the primary into the current workspace |
| Copy with Worktrunk syntax | `wt step copy-ignored --force` | Existing files are skipped unless `--force` is set |

`wt remove` and `wt list` are aliases for `wt rm` and `wt ls`.

The dotfiles zsh wrapper captures the path printed by `wt switch` and changes
the current shell into the target workspace. The executable prints the path
because a child process cannot change its parent shell's directory. Start a
new zsh or run `source ~/.zshrc` after installing the wrapper.

## Worktrunk mapping

| Worktrunk | wt / jj | Notes |
| --- | --- | --- |
| `wt switch -c feat` | `wt switch -c feat` | herdr-jj handles opening and focus |
| `wt switch -c feat --base main` | `wt switch -c feat -r 'trunk()'` | wt accepts a jj revset, not a branch |
| `wt remove` | `wt rm` | jj commits survive workspace removal |
| `wt step copy-ignored --force` | Same | Default copies preserve existing workspace files |
| `pre-switch`, `pre-start` | Same | Sequential and blocking |
| `post-start` | Same name | Blocking in the CLI; deferred before `post-switch` in the herdr setup pane |
| `post-switch` | Same | Runs after every successful CLI switch result |
| `[pre-remove]` | `[pre-remove]` | Failures warn but do not strand the workspace |
| `{{ branch }}` | Same | Means the jj workspace name; no bookmark ceremony |
| `{{ branch \| hash_port }}` | Same | The same filter syntax is supported |
| `worktree-path` | Same | Alias for `workspace-path`; the latter wins in one file |

## Configuration

User configuration lives at `~/.config/wt/config.toml`. Project configuration
lives at `<primary-workspace>/.config/wt.toml`. User hooks run first; project
hooks append. Project path settings override user settings. `workspace-path`
wins over `worktree-path` within one file. Excludes are combined.

```toml
# ~/.config/wt/config.toml
workspace-path = "~/.herdr/workspaces/{{ repo }}/{{ name | sanitize }}"

[copy-ignored]
exclude = [".cache/", ".turbo/"]
```

```toml
# <repo>/.config/wt.toml
[pre-start]
copy-envs = "wt copy-ignored"
env = "WORKSPACE_NAME='{{ name }}' COMPOSE_NAME='{{ name | sanitize_db }}' APP_PORT='{{ name | hash_port }}' POSTGRES_PORT='{{ ('db-' ~ name) | hash_port }}' DB_NAME='{{ name | sanitize_db }}' MINIO_PORT='{{ ('minio-' ~ name) | hash_port }}' MINIO_CONSOLE_PORT='{{ ('minio-console-' ~ name) | hash_port }}' wt env"
install = "vp i"
compose = "docker compose --env-file .env.compose up -d --wait --remove-orphans postgres minio"

[pre-remove]
compose-down = "docker compose --env-file .env.compose down"

[copy-ignored]
exclude = [".env.development.local", ".env.compose"]
```

Each hook phase is a table of named shell commands, run in declaration order.
Arrays of single-command tables are also accepted. `post-create` remains a
legacy fallback for `pre-start`. Explicit `pre-start` hooks suppress all legacy
`post-create` hooks. A start hook failure leaves the new workspace for diagnosis.
`wt switch` still emits the destination, so the wrapper enters the workspace.
`pre-remove` runs every hook, prints failures, and continues removal.
`post-remove` runs after the directory is gone and the workspace is forgotten;
it also continues past failures and executes from the primary root, since the
workspace directory no longer exists.

For migration, `[step.copy-ignored]` and `[copy-ignored]` are accepted. An
existing repository-root `.worktreeinclude` restricts copies with Git wildmatch
patterns. It supports comments, negation, `**`, anchored paths, and directories.
The file and configured includes intersect. Configured excludes always win.
Native non-colocated jj repositories use `jj file list` and root `.gitignore`.

`[list].url` renders as a final `wt ls` column. jj-ws does not probe the URL.
`[switch].base` is accepted as unused TOML. jj-ws bases creation on `@`.

## Template reference

| Variable | Value |
| --- | --- |
| `{{ name }}` | jj workspace name |
| `{{ branch }}` | Alias for the jj workspace name |
| `{{ repo }}` | Primary workspace directory name |
| `{{ workspace_path }}` | Absolute target workspace path |
| `{{ worktree_path }}` | Alias for the target workspace path |
| `{{ worktree_name }}` | Target workspace directory name |
| `{{ primary_path }}` | Absolute primary workspace path |
| `{{ repo_path }}` | Alias for the primary workspace path |
| `{{ primary_worktree_path }}` | Alias for the primary workspace path |
| `{{ cwd }}` | Hook execution directory, in hooks |
| `{{ hook_type }}` | Lifecycle phase, in hooks |
| `{{ hook_name }}` | Named command, in hooks |

| Filter | Effect |
| --- | --- |
| `sanitize` | Replaces `/` and `\` with `-` |
| `sanitize_db` | Produces a lower-case database identifier with a hash suffix |
| `sanitize_hash` | Sanitizes and adds a hash only when the input changed |
| `hash_port` | Produces a stable port in `10000..19999` |

String concatenation is supported for distinct ports:
`{{ ('db-' ~ name) | hash_port }}`.

## jj semantic differences

jj-ws maps a Worktrunk branch to a jj workspace. It does not create bookmarks,
inspect Git branch state, query CI, or probe list URLs. All hooks run sequentially.
CLI post hooks block. The herdr wizard defers all start hooks into a setup pane.
The limited template engine supports variables, one filter, parentheses, quoted
strings, and `~` concatenation. It does not support general Jinja control syntax.
Template values are quoted for one shell parse. Do not embed templates inside
`sh -c`, `bash -c`, or another nested shell command. Use direct hook commands.

Workspace names accept letters, digits, `.`, `_`, `-`, and safe `/` separators.
The names `.` and `..`, traversal segments, absolute paths, whitespace, and shell
metacharacters are rejected before repository access, hooks, or filesystem work.
Built-in destination paths use `sanitize_hash`. Safe names remain unchanged,
while slash names gain a short suffix to avoid slash/hyphen collisions.

`wt switch --create --force` restores an existing destination when jj creation
fails. If jj leaves partial output, jj-ws preserves it beside the restored path.
`--force` never replaces a path registered to another jj workspace.

## Removal model

`jj workspace forget` only forgets the working copy. Its commits remain in jj's
history and operation log. The confirmation prompt protects ignored and other
untracked files that directory removal would actually destroy.
