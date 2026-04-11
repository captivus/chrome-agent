#!/usr/bin/env bash
#
# Release to PyPI via GitHub Releases.
#
# Usage:
#   ./scripts/release.sh                # suggests next minor version
#   ./scripts/release.sh 0.3.0          # use a specific version
#   ./scripts/release.sh --dry-run      # show what would happen
#   ./scripts/release.sh --dry-run 0.3.0
#
# What it does:
#   1. Suggests or validates the version number
#   2. Bumps the version in pyproject.toml and commits
#   3. Verifies uv build works
#   4. Creates a git tag and pushes it
#   5. Creates a GitHub release with auto-generated notes
#   6. Watches the publish workflow
#
# Prerequisites:
#   - gh CLI authenticated (gh auth login)
#   - PyPI Trusted Publishing configured for this repo
#   - Remote is set up and current branch is pushed

set -euo pipefail

# --- Parse flags ---

DRY_RUN=false
POSITIONAL_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        *) POSITIONAL_ARGS+=("$arg") ;;
    esac
done

# --- Read current state ---

CURRENT_VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
PACKAGE_NAME=$(grep '^name' pyproject.toml | head -1 | sed 's/name = "\(.*\)"/\1/')
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || echo "unknown")

# --- Determine version ---

bump_minor() {
    local major minor patch
    IFS='.' read -r major minor patch <<< "$1"
    echo "${major}.$((minor + 1)).0"
}

if [ ${#POSITIONAL_ARGS[@]} -ge 1 ]; then
    VERSION="${POSITIONAL_ARGS[0]}"
else
    SUGGESTED=$(bump_minor "$CURRENT_VERSION")
    echo "Current version: $CURRENT_VERSION"
    read -p "Release version [$SUGGESTED]: " -r VERSION
    VERSION="${VERSION:-$SUGGESTED}"
fi

if ! echo "$VERSION" | grep --quiet --extended-regexp '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: Version must be semver (MAJOR.MINOR.PATCH), got: $VERSION"
    exit 1
fi

if [ "$VERSION" = "$CURRENT_VERSION" ]; then
    echo "ERROR: Version $VERSION is the same as the current version"
    exit 1
fi

TAG="v${VERSION}"

# --- Pre-flight checks ---

echo ""
echo "=== Pre-flight checks ==="

# Clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree is not clean. Commit or stash changes first."
    git status --short
    exit 1
fi
echo "  Working tree is clean"

# Tag doesn't already exist (check both local and remote)
if git tag --list "$TAG" | grep --quiet "$TAG"; then
    echo "ERROR: Tag $TAG already exists locally"
    exit 1
fi
if git ls-remote --tags origin 2>/dev/null | grep --quiet "refs/tags/$TAG"; then
    echo "ERROR: Tag $TAG already exists on remote"
    exit 1
fi
echo "  Tag $TAG is available"

# Build works
echo "  Building..."
uv build --quiet 2>&1
echo "  Build succeeded"

# --- Release notes preview ---

# Find the previous tag to generate notes from
PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

echo ""
echo "=== Release plan: $PACKAGE_NAME $TAG ==="
echo ""
echo "  1. Bump version $CURRENT_VERSION -> $VERSION in pyproject.toml"
echo "  2. Commit: \"Release $TAG\""
echo "  3. Create git tag $TAG"
echo "  4. Push commit and tag to origin"
echo "  5. Create GitHub release with auto-generated notes"
echo "  6. Trigger publish workflow -> PyPI"
echo ""
echo "  PyPI: https://pypi.org/project/$PACKAGE_NAME/$VERSION/"
echo "  GitHub: https://github.com/$REPO/releases/tag/$TAG"

echo ""
echo "=== Commits since ${PREV_TAG:-inception} ==="
echo ""
if [ -n "$PREV_TAG" ]; then
    git log "${PREV_TAG}..HEAD" --oneline
else
    git log --oneline
fi

echo ""
echo "=== Release notes preview ==="
echo ""
if [ -n "$PREV_TAG" ]; then
    gh api "repos/$REPO/releases/generate-notes" \
        --method POST \
        --field tag_name="$TAG" \
        --field previous_tag_name="$PREV_TAG" \
        --field target_commitish="$(git rev-parse HEAD)" \
        --jq '.body' 2>/dev/null || echo "(could not generate preview)"
else
    gh api "repos/$REPO/releases/generate-notes" \
        --method POST \
        --field tag_name="$TAG" \
        --field target_commitish="$(git rev-parse HEAD)" \
        --jq '.body' 2>/dev/null || echo "(could not generate preview -- first release)"
fi

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "(dry run -- nothing was changed)"
    exit 0
fi

echo ""
read -p "Proceed? [y/N] " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# --- Bump version and commit ---

echo ""
echo "=== Bumping version ==="

sed -i "s/^version = \"$CURRENT_VERSION\"/version = \"$VERSION\"/" pyproject.toml
echo "  Updated pyproject.toml: $CURRENT_VERSION -> $VERSION"

git add pyproject.toml
# Include uv.lock if it changed from the version bump
uv lock --quiet 2>/dev/null || true
git add uv.lock 2>/dev/null || true

git commit --quiet -m "Release $TAG"
echo "  Committed: Release $TAG"

# --- Tag and push ---

echo ""
echo "=== Creating release ==="

git tag "$TAG"
echo "  Created tag $TAG"

git push origin HEAD "$TAG"
echo "  Pushed to origin"

gh release create "$TAG" \
    --title "$TAG" \
    --generate-notes
echo "  GitHub release created"

# --- Watch workflow ---

echo ""
echo "=== Watching publish workflow ==="

RUN_ID=""
for attempt in 1 2 3 4 5 6; do
    sleep 5
    RUN_ID=$(gh run list --workflow=publish.yml --limit=1 --json databaseId --jq '.[0].databaseId')
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
    echo "  PyPI: https://pypi.org/project/$PACKAGE_NAME/$VERSION/"
    echo "  GitHub: https://github.com/$REPO/releases/tag/$TAG"
else
    echo "  Could not find workflow run after 30s. Check manually:"
    echo "  https://github.com/$REPO/actions"
fi
