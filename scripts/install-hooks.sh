#!/usr/bin/env bash
#
# install-hooks.sh — installs git hooks into .git/hooks/
#
# Since .git/hooks/ is not under version control, new clones don't get
# the pre-commit hook automatically. Run this script once after cloning:
#
#   bash scripts/install-hooks.sh
#
# It copies scripts/hooks/* into .git/hooks/ and makes them executable.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
  echo "error: not inside a git repository" >&2
  exit 1
fi

SRC="$REPO_ROOT/scripts/hooks"
DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$SRC" ]; then
  echo "error: $SRC not found" >&2
  exit 1
fi

mkdir -p "$DST"
for hook in "$SRC"/*; do
  name="$(basename "$hook")"
  cp "$hook" "$DST/$name"
  chmod +x "$DST/$name"
  echo "installed: .git/hooks/$name"
done

echo ""
echo "done. Hooks active."
