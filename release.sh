#!/usr/bin/env bash
set -euo pipefail

# === Audit Engine — Local Release Script ===
# Builds distribution ZIP, creates GitHub tag + release.
# No dependency on GitHub Actions or any CI.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Read version ---
VERSION=$(python3 -c "
import re
with open('pdf_generator_ui.py') as f:
    for line in f:
        if line.startswith('VERSION'):
            print(re.search(r'[\x27\"](.+)[\x27\"]', line).group(1))
            break
")
TAG="v${VERSION}"
ZIP="Audit_Engine_${TAG}.zip"

echo "==> Version: $VERSION"

# --- Check if tag already exists on remote ---
if git ls-remote --tags origin "$TAG" | grep -q .; then
  echo "!!> Tag $TAG already exists on remote."
  echo "    Bump VERSION in pdf_generator_ui.py first."
  exit 1
fi

# --- Build distribution ---
echo "==> Building $ZIP ..."
python3 create_distribution_zip.py

if [ ! -f "$ZIP" ]; then
  echo "!!> Failed to create $ZIP"
  exit 1
fi

# --- Create and push tag ---
echo "==> Creating tag $TAG ..."
git tag "$TAG"
git push origin "$TAG"

# --- Create GitHub release ---
echo "==> Creating GitHub release ..."
gh release create "$TAG" \
  --title "$TAG" \
  --notes "## Audit Engine ${VERSION}

Auto-generated release.

- Commit: $(git rev-parse --short HEAD)
- ZIP: \`${ZIP}\`" \
  "$ZIP"

# --- Clean up local ZIP ---
rm -f "$ZIP"

echo "==> Done: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/releases/tag/$TAG"
