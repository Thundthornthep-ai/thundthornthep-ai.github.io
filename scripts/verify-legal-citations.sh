#!/usr/bin/env bash
# LAS Legal Citation Firewall — fail-closed pre-publish gate
#
# Usage:
#   bash scripts/verify-legal-citations.sh              # changed pages in scope
#   bash scripts/verify-legal-citations.sh --all        # every page in scope
#   bash scripts/verify-legal-citations.sh file.html …  # explicit files
#
# Scope: every tracked articles/*.html and en/articles/*.html, plus the blog/ and
# en/blog/ pages registered as legally reviewed in learning-hub/legal-reviews.json
# (scripts/las_public_pages.py). Other blog pages are outside the Knowledge Hub.
#
# The firewall runs once for the whole file list (the registry loads once) and
# prints one [PASS] / [BLOCK] line per file. Exit 2 from the firewall ("no
# statutory citation") means the page has no section-like text at all; exit 4
# ("section-like text could not be parsed") is a BLOCK, never a pass.
#
# The firewall and its local legal KB are deliberately external to this public
# repository. Configure LAS_CITATION_FIREWALL and LAS_LEGAL_KB in the
# execution environment; an absent or unreadable dependency is a hard failure.

set -euo pipefail

readonly PYTHON_BIN="${PYTHON_BIN:-python3}"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# A release may override these with the internal LAS verifier/KB locally. The
# repository defaults are public, release-scoped, and contain no restricted
# source material, so the GitHub gate remains executable and fail-closed.
readonly FIREWALL="${LAS_CITATION_FIREWALL:-${SCRIPT_DIR}/public-citation-firewall.py}"
readonly KB="${LAS_LEGAL_KB:-${SCRIPT_DIR}/legal-kb}"

die() {
    echo "[CITATION-CHECK] ERROR: $*" >&2
    exit 1
}

SCOPE_LIST="$(mktemp)"
REPORT="$(mktemp)"
trap 'rm -f "$SCOPE_LIST" "$REPORT"' EXIT

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "Python interpreter not found: $PYTHON_BIN"
"$PYTHON_BIN" -X utf8 "${SCRIPT_DIR}/las_public_pages.py" citation-scope > "$SCOPE_LIST" \
    || die "cannot list the gated pages (learning-hub/legal-reviews.json)"

in_scope() {
    case "$1" in
        articles/*.html|en/articles/*.html) return 0 ;;
    esac
    grep -qxF -- "$1" "$SCOPE_LIST"
}

declare -a FILES=()

if [[ "${1:-}" == "--all" ]]; then
    shift
    [[ "$#" -eq 0 ]] || die "--all cannot be combined with file arguments"
    while IFS= read -r file; do
        FILES+=("$file")
    done < "$SCOPE_LIST"
elif [[ "$#" -gt 0 ]]; then
    while [[ "$#" -gt 0 ]]; do
        in_scope "$1" || die "not an article or reviewed blog HTML path: $1"
        FILES+=("$1")
        shift
    done
else
    # HEAD diff covers both staged and unstaged tracked changes. Include
    # untracked article files so a new article cannot bypass the gate locally.
    while IFS= read -r file; do
        if in_scope "$file"; then
            FILES+=("$file")
        fi
    done < <(
        {
            git diff --name-only --diff-filter=ACMR HEAD
            git ls-files --others --exclude-standard -- 'articles/*.html' 'en/articles/*.html'
        } | sort -u
    )
fi

if [[ "${#FILES[@]}" -eq 0 ]]; then
    echo "[CITATION-CHECK] No changed article HTML — nothing to verify"
    exit 0
fi

[[ -f "$FIREWALL" && -r "$FIREWALL" ]] || die "Citation Firewall is missing or unreadable (set LAS_CITATION_FIREWALL)"
[[ -d "$KB" && -r "$KB" ]] || die "Legal KB is missing or unreadable (set LAS_LEGAL_KB)"

echo "=========================================="
echo "  LAS Citation Firewall — HARD GATE"
echo "  Files: ${#FILES[@]}"
echo "=========================================="

status=0
if [[ "$FIREWALL" -ef "${SCRIPT_DIR}/public-citation-firewall.py" ]]; then
    "$PYTHON_BIN" -X utf8 "$FIREWALL" \
        --batch \
        --input "${FILES[@]}" \
        --kb "$KB" \
        --mode hard-gate \
        --no-pinecone 2>&1 | tee "$REPORT" || status=$?
else
    # An external verifier (LAS_CITATION_FIREWALL) may not know --batch: call it per file with the same verdicts.
    for file in "${FILES[@]}"; do
        echo "Checking: $file"
        rc=0
        "$PYTHON_BIN" -X utf8 "$FIREWALL" --input "$file" --kb "$KB" --mode hard-gate --no-pinecone || rc=$?
        case "$rc" in
            0) echo "[PASS] $file — citations verified" ;;
            2) echo "[PASS] $file — no statutory citation detected" ;;
            *) echo "[BLOCK] $file — firewall exit $rc" ;;
        esac
        if [[ "$rc" -ne 0 && "$rc" -ne 2 && "$status" -eq 0 ]]; then
            status="$rc"
        fi
    done 2>&1 | tee "$REPORT"
    if grep -q '^\[BLOCK\]' "$REPORT"; then
        status="$(sed -n 's/^\[BLOCK\] .* — firewall exit \([0-9]*\).*/\1/p' "$REPORT" | head -1)"
        [[ -n "$status" ]] || status=1
    fi
fi

failed="$(grep -c '^\[BLOCK\]' "$REPORT" || true)"
passed="$(grep -c '^\[PASS\]' "$REPORT" || true)"

echo "=========================================="
if [[ "$status" -ne 0 || "$failed" -gt 0 ]]; then
    [[ "$status" -ne 0 ]] || status=1
    echo "RESULT: $failed file(s) blocked"
    exit "$status"
fi
if [[ "$passed" -ne "${#FILES[@]}" ]]; then
    echo "RESULT: firewall reported $passed verdict(s) for ${#FILES[@]} file(s)" >&2
    exit 1
fi
echo "RESULT: all files passed citation gate"
