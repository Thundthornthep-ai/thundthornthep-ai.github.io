#!/usr/bin/env bash
# Unit tests for scripts/resolve-validate-range.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="${SCRIPT_DIR}/resolve-validate-range.sh"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
failures=0

assert_eq() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$expected" != "$actual" ]]; then
    echo "FAIL  ${name}"
    echo "      expected: ${expected}"
    echo "      actual:   ${actual}"
    failures=$((failures + 1))
  else
    echo "PASS  ${name}"
  fi
}

parse_field() {
  local blob="$1" key="$2"
  printf '%s\n' "$blob" | sed -n "s/^${key}=//p" | tail -1
}

echo "== isolated repo =="
tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

git -C "$tmp" init -q
git -C "$tmp" config user.email "validate-range-test@example.com"
git -C "$tmp" config user.name "Validate Range Test"
git -C "$tmp" config commit.gpgsign false
printf 'one\n' > "${tmp}/file.txt"
git -C "$tmp" add file.txt
git -C "$tmp" commit -q -m "root"
root="$(git -C "$tmp" rev-parse HEAD)"
printf 'two\n' > "${tmp}/file.txt"
git -C "$tmp" commit -q -am "second"
second="$(git -C "$tmp" rev-parse HEAD)"
printf 'three\n' > "${tmp}/file.txt"
git -C "$tmp" commit -q -am "third"
third="$(git -C "$tmp" rev-parse HEAD)"

run_resolver() {
  (cd "$tmp" && env "$@" bash "$RESOLVER")
}

out="$(run_resolver EVENT_NAME=push PUSH_BEFORE="$second" TARGET="$third")"
assert_eq "push keeps event.before" "$second" "$(parse_field "$out" base)"
assert_eq "push target is sha" "$third" "$(parse_field "$out" target)"
assert_eq "push reason" "event.before..sha" "$(parse_field "$out" reason)"

out="$(run_resolver EVENT_NAME=workflow_dispatch PUSH_BEFORE="" TARGET="$third")"
assert_eq "dispatch base is first parent" "$second" "$(parse_field "$out" base)"
assert_eq "dispatch target is sha" "$third" "$(parse_field "$out" target)"
assert_eq "dispatch reason" "first-parent fallback (no usable event.before)" "$(parse_field "$out" reason)"

zeros="0000000000000000000000000000000000000000"
out="$(run_resolver EVENT_NAME=push PUSH_BEFORE="$zeros" TARGET="$third")"
assert_eq "zero before uses first parent" "$second" "$(parse_field "$out" base)"

out="$(run_resolver EVENT_NAME=pull_request PR_BASE="$root" PR_HEAD="$third" TARGET="$third")"
assert_eq "pr base" "$root" "$(parse_field "$out" base)"
assert_eq "pr head" "$third" "$(parse_field "$out" target)"
assert_eq "pr reason" "pull_request base..head" "$(parse_field "$out" reason)"

out="$(run_resolver EVENT_NAME=workflow_dispatch PUSH_BEFORE="" TARGET="$root")"
assert_eq "root commit falls back to itself" "$root" "$(parse_field "$out" base)"
assert_eq "root commit reason" "root fallback (target has no parent)" "$(parse_field "$out" reason)"

echo "== real merge SHA from the failed dispatch =="
merge="1424fb84066f9a8b9b7218388e31233e60a5a1de"
parent="f424287ac309df024cbd44b552dbd3cf6e38fab9"
out="$(cd "$REPO_ROOT" && EVENT_NAME=workflow_dispatch PUSH_BEFORE="" TARGET="$merge" bash "$RESOLVER")"
assert_eq "failed dispatch SHA uses merge first parent" "$parent" "$(parse_field "$out" base)"
out="$(cd "$REPO_ROOT" && EVENT_NAME=push PUSH_BEFORE="$parent" TARGET="$merge" bash "$RESOLVER")"
assert_eq "successful push SHA keeps before" "$parent" "$(parse_field "$out" base)"

series_globs=(
  'articles/las-share-[0-9][0-9].html'
  'articles/las-shield-[0-9][0-9].html'
  'articles/las-cc-[0-9][0-9].html'
  'articles/las-upsize-[0-9][0-9].html'
  'articles/las-invest-[0-9][0-9].html'
)
dispatch_files="$(cd "$REPO_ROOT" && git diff --name-only "$parent" "$merge" -- "${series_globs[@]}")"
if printf '%s\n' "$dispatch_files" | grep -q 'las-invest-'; then
  echo "FAIL  first-parent range must not include unpublished LAS INVEST files"
  echo "$dispatch_files"
  failures=$((failures + 1))
else
  echo "PASS  first-parent range excludes LAS INVEST drafts"
fi
if ! printf '%s\n' "$dispatch_files" | grep -q 'articles/las-cc-11.html'; then
  echo "FAIL  first-parent range should still include C&C files from PR #10"
  echo "$dispatch_files"
  failures=$((failures + 1))
else
  echo "PASS  first-parent range still includes the PR #10 C&C release"
fi

if ((failures > 0)); then
  echo
  echo "${failures} assertion(s) failed"
  exit 1
fi
echo
echo "All resolve-validate-range checks passed."
