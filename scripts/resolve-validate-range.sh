#!/usr/bin/env bash
# Resolve the incremental comparison range for the exact-slug/series gate.
#
# The gate is meant to check LAS series HTML that changed in the current
# release, not every series file since the first commit.
#
# workflow_dispatch (and force-pushes whose `before` is all zeros) have no
# usable github.event.before. The previous fallback used the repo root, which
# re-validates unpublished drafts such as LAS INVEST and fails a re-run of a
# SHA whose push-path Validate already passed.
#
# Inputs (env):
#   EVENT_NAME    github.event_name
#   PR_BASE       github.event.pull_request.base.sha
#   PR_HEAD       github.event.pull_request.head.sha
#   PUSH_BEFORE   github.event.before
#   TARGET        github.sha (defaults to HEAD)
#
# Prints GitHub Actions output lines:
#   base=<sha>
#   target=<sha>
#   reason=<why this range was chosen>

set -euo pipefail

EVENT_NAME="${EVENT_NAME:-}"
PR_BASE="${PR_BASE:-}"
PR_HEAD="${PR_HEAD:-}"
PUSH_BEFORE="${PUSH_BEFORE:-}"
TARGET="${TARGET:-${GITHUB_SHA:-}}"

if [[ -z "$TARGET" ]]; then
  TARGET="$(git rev-parse HEAD)"
fi

is_usable_commit() {
  local sha="${1:-}"
  [[ -n "$sha" ]] || return 1
  [[ ! "$sha" =~ ^0+$ ]] || return 1
  git cat-file -e "${sha}^{commit}" 2>/dev/null
}

base=""
target=""
reason=""

if [[ "$EVENT_NAME" == "pull_request" ]]; then
  base="$PR_BASE"
  target="$PR_HEAD"
  reason="pull_request base..head"
else
  base="$PUSH_BEFORE"
  target="$TARGET"
  reason="event.before..sha"
fi

if ! is_usable_commit "$target"; then
  echo "ERROR: target is not a usable commit: ${target:-'(empty)'}" >&2
  exit 1
fi

if ! is_usable_commit "$base"; then
  if parent="$(git rev-parse --verify "${target}^" 2>/dev/null)"; then
    base="$parent"
    reason="first-parent fallback (no usable event.before)"
  else
    base="$(git rev-list --max-parents=0 "$target" | tail -1)"
    reason="root fallback (target has no parent)"
  fi
fi

printf 'base=%s\n' "$base"
printf 'target=%s\n' "$target"
printf 'reason=%s\n' "$reason"
