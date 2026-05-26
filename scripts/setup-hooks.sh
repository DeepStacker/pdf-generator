#!/usr/bin/env bash
set -euo pipefail

HOOKS_DIR=".githooks"
if git config core.hooksPath | grep -q "$HOOKS_DIR"; then
    echo "✔ Hooks already configured at $HOOKS_DIR"
else
    git config core.hooksPath "$HOOKS_DIR"
    echo "✔ Git hooks path set to $HOOKS_DIR"
fi
