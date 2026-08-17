# WSL configuration

This directory is the source of truth for:

- `wsl.conf` -> `/etc/wsl.conf`
- `hosts` -> `/etc/hosts`
- `.wslconfig` -> `%UserProfile%\.wslconfig`

Apply all files from WSL:

```bash
~/dotfiles/misc/wsl/sync
```

The hosts override bypasses a Global Secure Access limitation: GSA maps Entra
authentication to synthetic `6.6.x.x` addresses but does not route them for WSL.
If the pinned public address stops responding, obtain a current address from
public DNS and update `hosts` before syncing.
