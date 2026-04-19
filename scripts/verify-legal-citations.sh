#!/bin/bash
# LAS Legal Citation Pre-Publish Verification
# Runs Citation Firewall on all staged .html article files before commit
# Created: 2026-04-20 (after ม.90 incident)
#
# Usage: Called by pre-commit hook or manually:
#   bash scripts/verify-legal-citations.sh [file.html]

set -e

FIREWALL="$HOME/.claude/skills/las-citation-firewall/verify.py"
KB="C:/Users/thund/OneDrive/เดสก์ท็อป/ACT LAW/000000000_LAS_Knowledge/las_legal_kb"

if [ ! -f "$FIREWALL" ]; then
    echo "[SKIP] Citation Firewall not found at $FIREWALL"
    exit 0
fi

# If specific file provided, check that file only
if [ -n "$1" ]; then
    FILES="$1"
else
    # Check all staged article HTML files
    FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '^(articles|en/articles)/.*\.html$' || true)
fi

if [ -z "$FILES" ]; then
    echo "[CITATION-CHECK] No article files staged — skipping"
    exit 0
fi

echo "=========================================="
echo "  LAS Citation Firewall — Pre-Publish QC"
echo "=========================================="

FAILED=0
for f in $FILES; do
    echo ""
    echo "Checking: $f"
    python -X utf8 "$FIREWALL" --input "$f" --kb "$KB" --mode report 2>&1 || true
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 1 ]; then
        echo "[BLOCK] $f — Citations failed verification!"
        FAILED=$((FAILED + 1))
    elif [ $EXIT_CODE -eq 0 ]; then
        echo "[PASS] $f — All citations verified"
    elif [ $EXIT_CODE -eq 2 ]; then
        echo "[SKIP] $f — No citations detected"
    fi
done

echo ""
echo "=========================================="
if [ $FAILED -gt 0 ]; then
    echo "  RESULT: $FAILED file(s) FAILED citation check"
    echo "  ACTION: Fix citations before committing"
    echo "=========================================="
    exit 1
else
    echo "  RESULT: All files passed citation check"
    echo "=========================================="
    exit 0
fi
