#!/usr/bin/env bash
#
# Release chrome-agent to PyPI via GitHub Releases.
#
# Usage: ./scripts/release.sh <version>
#   e.g. ./scripts/release.sh 0.1.0
#
# What it does:
#   1. Validates clean working tree and version format
#   2. Verifies pyproject.toml version matches the argument
#   3. Verifies uv build works
#   4. Creates a git tag v<version>
#   5. Pushes the tag
#   6. Creates a GitHub release with auto-generated notes
#   7. Watches the publish workflow
#
# Prerequisites:
#   - gh CLI authenticated (gh auth login)
#   - PyPI Trusted Publishing configured for this repo
#   - Remote is set up and current branch is pushed

set -euo pipefail

# --- Argument validation ---

if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "  e.g. $0 0.1.0"
    exit 1
fi

VERSION="$1"

if ! echo "$VERSION" | grep --quiet --extended-regexp '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: Version must be semver (MAJOR.MINOR.PATCH), got: $VERSION"
    exit 1
fi

TAG="v${VERSION}"

# --- Pre-flight checks ---

echo "=== Pre-flight checks ==="

# Clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree is not clean. Commit or stash changes first."
    git status --short
    exit 1
fi
echo "  Working tree is clean"

# Version in pyproject.toml matches
TOML_VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
if [ "$TOML_VERSION" != "$VERSION" ]; then
    echo "ERROR: pyproject.toml version is $TOML_VERSION, but you requested $VERSION"
    echo "  Update pyproject.toml first, commit, then run this script."
    exit 1
fi
echo "  pyproject.toml version matches: $VERSION"

# Tag doesn't already exist
if git tag --list "$TAG" | grep --quiet "$TAG"; then
    echo "ERROR: Tag $TAG already exists"
    exit 1
fi
echo "  Tag $TAG is available"

# Build works
echo "  Building..."
uv build --quiet 2>&1
echo "  Build succeeded"

echo ""
echo "=== Ready to release $TAG ==="
echo ""
echo "This will:"
echo "  1. Create git tag $TAG"
echo "  2. Push tag to origin"
echo "  3. Create GitHub release with auto-generated notes"
echo "  4. Trigger the publish workflow (PyPI)"
echo ""
read -p "Proceed? [y/N] " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# --- Release ---

echo ""
echo "=== Creating release ==="

git tag "$TAG"
echo "  Created tag $TAG"

git push origin "$TAG"
echo "  Pushed tag to origin"

gh release create "$TAG" \
    --title "$TAG" \
    --generate-notes
echo "  GitHub release created"

# --- Watch workflow ---

echo ""
echo "=== Watching publish workflow ==="

# Poll for the workflow run (GitHub can take a few seconds to trigger it)
RUN_ID=""
for attempt in 1 2 3 4 5 6; do
    sleep 5
    RUN_ID=$(gh run list --workflow=publish.yml --limit=1 --json databaseId,createdAt --jq '.[0].databaseId')
    if [ -n "$RUN_ID" ]; then
        echo "  Found workflow run: $RUN_ID"
        break
    fi
    echo "  Waiting for workflow to start (attempt $attempt/6)..."
done

if [ -n "$RUN_ID" ]; then
    gh run watch "$RUN_ID"
    echo ""
    echo "=== Done ==="
    echo "  PyPI: https://pypi.org/project/chrome-agent/$VERSION/"
    echo "  GitHub: https://github.com/captivus/chrome-agent/releases/tag/$TAG"
else
    echo "  Could not find workflow run after 30s. Check manually:"
    echo "  https://github.com/captivus/chrome-agent/actions"
fi
