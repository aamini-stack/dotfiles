# wt

`wt` creates and removes jj workspaces, copies ignored files, and runs project
lifecycle hooks. It does not know about herdr; herdr-jj wraps it with workspace
focus, panes, and status reporting.

## Core commands

| Task | Command | Notes |
| --- | --- | --- |
| Switch to a workspace | `wt switch feat` | Prints the path; the zsh wrapper cds into it |
| Pick a workspace with fzf | `wt switch` | No name opens an interactive picker |
| Create and switch | `wt switch -c feat` | Bases the workspace on `@` and runs `post-create` hooks |
| Create from another revision | `wt switch -c feat -r 'trunk()'` | Accepts any jj revset |
| List workspaces | `wt ls` | Shows names, paths, and the current workspace |
| Remove by name | `wt rm feat` | Confirms, runs `pre-remove`, forgets, then removes the directory |
| Remove the current workspace | `wt rm` | The primary workspace is never removable |
| Remove without a prompt | `wt rm feat --yes` | Intended for trusted integrations such as herdr-jj |
| Run a named hook | `wt hook copy-envs` | Searches `post-create` and `pre-remove` hooks |
| Copy ignored files | `wt copy-ignored` | Copies from the primary into the current workspace |

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
| `wt step copy-ignored --force` | `wt copy-ignored` | wt overwrites copied ignored files |
| `[[pre-start]]` | `[[post-create]]` | Sequential and blocking |
| `[[post-start]]` server hooks | herdr panes | Long-running processes are not lifecycle hooks |
| `[pre-remove]` | `[pre-remove]` | Failures warn but do not strand the workspace |
| `{{ branch }}` | `{{ name }}` | jj workspace name; no bookmark ceremony |
| `{{ branch \| hash_port }}` | `{{ name \| hash_port }}` | The same filter syntax is supported |
| `worktree-path` | `workspace-path` | Defaults under `~/.herdr/workspaces` |

## Configuration

User configuration lives at `~/.config/wt/config.toml`. Project configuration
lives at `<primary-workspace>/.config/wt.toml`. User hooks run first; project
hooks append. Excludes are combined.

```toml
# ~/.config/wt/config.toml
workspace-path = "~/.herdr/workspaces/{{ repo }}/{{ name | sanitize }}"

[copy-ignored]
exclude = [".cache/", ".turbo/"]
```

```toml
# <repo>/.config/wt.toml
[[post-create]]
copy-envs = "wt copy-ignored"

[[post-create]]
env = "WORKSPACE_NAME='{{ name }}' COMPOSE_NAME='{{ name | sanitize_db }}' APP_PORT='{{ name | hash_port }}' POSTGRES_PORT='{{ ('db-' ~ name) | hash_port }}' DB_NAME='{{ name | sanitize_db }}' MINIO_PORT='{{ ('minio-' ~ name) | hash_port }}' MINIO_CONSOLE_PORT='{{ ('minio-console-' ~ name) | hash_port }}' wt-generate-env"

[[post-create]]
install = "vp i"

[[post-create]]
compose = "docker compose --env-file .env.compose up -d --wait --remove-orphans postgres minio"

[pre-remove]
compose-down = "docker compose --env-file .env.compose down"

[copy-ignored]
exclude = [".env.development.local", ".env.compose"]
```

Each hook table contains one named shell command. `post-create` stops at the
first failure and leaves the new workspace in place for diagnosis.
`pre-remove` runs every hook, prints failures, and continues removal.

For migration, `[step.copy-ignored] exclude` is also accepted.

## Template reference

| Variable | Value |
| --- | --- |
| `{{ name }}` | jj workspace name |
| `{{ repo }}` | Primary workspace directory name |
| `{{ workspace_path }}` | Absolute target workspace path |
| `{{ primary_path }}` | Absolute primary workspace path |

| Filter | Effect |
| --- | --- |
| `sanitize` | Replaces `/` and `\` with `-` |
| `sanitize_db` | Produces a lower-case database identifier with a hash suffix |
| `hash_port` | Produces a stable port in `10000..19999` |

String concatenation is supported for distinct ports:
`{{ ('db-' ~ name) | hash_port }}`.

## Removal model

`jj workspace forget` only forgets the working copy. Its commits remain in jj's
history and operation log. The confirmation prompt protects ignored and other
untracked files that directory removal would actually destroy.
