#!/usr/bin/env bash
# LAS Legal Citation Firewall — fail-closed pre-publish gate
#
# Usage:
#   bash scripts/verify-legal-citations.sh              # changed article HTML
#   bash scripts/verify-legal-citations.sh --all        # every tracked article
#   bash scripts/verify-legal-citations.sh file.html …  # explicit files
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

is_article_html() {
    case "$1" in
        articles/*.html|en/articles/*.html) return 0 ;;
        *) return 1 ;;
    esac
}

declare -a FILES=()

if [[ "${1:-}" == "--all" ]]; then
    shift
    [[ "$#" -eq 0 ]] || die "--all cannot be combined with file arguments"
    while IFS= read -r file; do
        FILES+=("$file")
    done < <(git ls-files -- 'articles/*.html' 'en/articles/*.html')
elif [[ "$#" -gt 0 ]]; then
    while [[ "$#" -gt 0 ]]; do
        is_article_html "$1" || die "not an article HTML path: $1"
        FILES+=("$1")
        shift
    done
else
    # HEAD diff covers both staged and unstaged tracked changes. Include
    # untracked article files so a new article cannot bypass the gate locally.
    while IFS= read -r file; do
        if is_article_html "$file"; then
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

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "Python interpreter not found: $PYTHON_BIN"
[[ -f "$FIREWALL" && -r "$FIREWALL" ]] || die "Citation Firewall is missing or unreadable (set LAS_CITATION_FIREWALL)"
[[ -d "$KB" && -r "$KB" ]] || die "Legal KB is missing or unreadable (set LAS_LEGAL_KB)"

echo "=========================================="
echo "  LAS Citation Firewall — HARD GATE"
echo "  Files: ${#FILES[@]}"
echo "=========================================="

failed=0
failure_status=1
for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "[BLOCK] $file — file does not exist" >&2
        failed=$((failed + 1))
        continue
    fi

    echo "Checking: $file"
    if "$PYTHON_BIN" -X utf8 "$FIREWALL" \
        --input "$file" \
        --kb "$KB" \
        --mode hard-gate \
        --no-pinecone; then
        echo "[PASS] $file — citations verified"
    else
        status=$?
        case "$status" in
            2) echo "[PASS] $file — no statutory citation detected" ;;
            *)
                echo "[BLOCK] $file — firewall exit $status" >&2
                if [[ "$failed" -eq 0 ]]; then
                    failure_status="$status"
                fi
                failed=$((failed + 1))
                ;;
        esac
    fi
done

echo "=========================================="
if [[ "$failed" -gt 0 ]]; then
    echo "RESULT: $failed file(s) blocked"
    exit "$failure_status"
fi
echo "RESULT: all files passed citation gate"
