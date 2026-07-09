# Lima host setup notes:
#
# Delete existing default instance:
#   limactl stop default
#   limactl remove default
#
# Create and start a Docker-template default instance:
#   limactl create --name default template:docker -y
#   limactl start --mount-none
#
# Reconnect manually:
#   ssh -F ~/.lima/default/ssh.config lima-default
#
# Resize the default instance:
#   limactl edit default --memory 12
#   limactl edit default --cpus 8
#   limactl edit default --disk 100
#
# Recreate with preferred resources:
#   limactl stop default && limactl remove default && limactl create --mount-none --cpus=4 --disk=100 --memory=12 default -y && limactl start && lima

[[ "$(uname -s)" == "Linux" ]] || return 0
getent hosts host.lima.internal >/dev/null 2>&1 || return 0

export OLLAMA_HOST="http://host.lima.internal:11434"

# Make sure iptables and mount.fuse3 are available.
export PATH="$PATH:/usr/sbin:/sbin"

# Keep Lima reconnects as plain SSH instead of going through `limactl shell`.
lima() {
  local instance="${LIMA_INSTANCE:-default}"
  ssh -F "$HOME/.lima/$instance/ssh.config" "lima-$instance" "$@"
}

# Auto-connect new interactive host shells to Herdr-on-Lima when available.
# Falls back to plain SSH for hosts without Herdr installed.
auto_lima() {
  local instance="${LIMA_AUTO_SSH_INSTANCE:-default}"
  local ssh_config="$HOME/.lima/$instance/ssh.config"
  local hostagent_socket="$HOME/.lima/$instance/ha.sock"
  local ssh_target="lima-$instance"

  [[ -o interactive ]] || return 0
  [[ -n "${LIMA_AUTO_SSH_DISABLED:-}" ]] && return 0
  [[ -n "${LIMA_AUTO_HERDR_DISABLED:-}" ]] && return 0
  [[ -n "${SSH_CONNECTION:-}" || -n "${SSH_TTY:-}" ]] && return 0
  [[ -n "${HERDR_ENV:-}" ]] && return 0
  [[ "${SHLVL:-1}" -gt 1 ]] && return 0
  [[ -t 0 && -t 1 ]] || return 0

  [[ -f "$ssh_config" ]] || return 0
  [[ -S "$hostagent_socket" ]] || return 0

  if command -v herdr >/dev/null 2>&1 && ssh -G "$ssh_target" 2>/dev/null | command grep -qi '^hostname 127\.0\.0\.1$'; then
    herdr --remote "$ssh_target"
  else
    ssh -F "$ssh_config" "$ssh_target"
  fi
}

auto_lima
