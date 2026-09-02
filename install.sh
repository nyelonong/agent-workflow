#!/bin/sh
set -eu
repo_dir="$(cd "$(dirname "$0")" && pwd -P)"
exec python3 "$repo_dir/scripts/install.py" "$@"
