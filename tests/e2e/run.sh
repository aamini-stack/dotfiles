#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
image="dotfiles-e2e"

docker_cmd="docker"
docker info &> /dev/null || docker_cmd="sudo docker"

# mise hits the GitHub API for release lookups; unauthenticated container
# traffic shares the host IP and hits the rate limit.
token_args=()
if token="$(gh auth token 2> /dev/null)"; then
  token_args=(-e "GITHUB_TOKEN=$token")
fi

$docker_cmd build -t "$image" "$here"
$docker_cmd run --rm \
  -e USER=test -e LOGNAME=test \
  "${token_args[@]}" \
  -v "$root:/opt/dotfiles-src:ro" \
  -v "$here/entrypoint.sh:/opt/e2e/entrypoint.sh:ro" \
  "$image" bash /opt/e2e/entrypoint.sh
