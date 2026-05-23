#!/usr/bin/env bash
# Install git hooks for auto-versioning and release
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

HOOKS_DIR="$REPO_DIR/.git/hooks"
mkdir -p "$HOOKS_DIR"

cp "$SCRIPT_DIR/pre-push" "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"

echo "==> Installed pre-push hook"
echo "    Next push to 'main' will:"
echo "      1. Auto-bump version (major.minor.<commit-count>)"
echo "      2. Build distribution ZIP"
echo "      3. Create git tag + GitHub release"
echo "      4. Push everything"
echo ""
echo "    To make changes without releasing, push to a different branch."
