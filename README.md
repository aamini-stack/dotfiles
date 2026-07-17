# Dotfiles

Bootstrap a fresh machine with:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/aria-amini/dotfiles/main/install.sh)
```

## Projects

The repository uses mise to manage tools and tasks across its projects. List
every project task with:

```bash
mise tasks --all
```

Common commands:

```bash
mise //:check             # Check every project
mise //:install           # Install personal tools
mise //tools/wt:test      # Test wt
mise //tools/wt:install   # Install wt
mise //infra:check        # Check the infrastructure project
```
