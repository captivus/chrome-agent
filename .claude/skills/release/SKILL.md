---
name: release
description: Release a new version to PyPI. Audits commits since the last release, suggests a version number, checks the README, and publishes. Usage - /release (version number is optional, will be suggested based on changes)
---

# Release Skill

You are performing a release of the `chrome-agent` project to PyPI.

## Important Rules

- Never reference yourself, Anthropic, or AI in commit messages or release notes
- Never list Claude as co-author
- Always use named parameters in function/tool calls
- Always use `uv` to run Python

## Release Process

Follow these steps in order. Do NOT skip steps or batch them up. Show the user what you find at each stage and get confirmation before proceeding.

### Step 1: Audit commits since the last release

- Read the current version from `pyproject.toml`
- Find the most recent release tag (e.g., `git describe --tags --abbrev=0`)
- List all commits since that tag: `git log <last_tag>..HEAD --oneline`
- For each commit, read the diff to understand what changed: `git show <hash> --stat` and `git show <hash>` as needed
- Categorize each change as: Added, Changed, Fixed, or Removed
- Ignore commits that are purely release housekeeping (version bumps)

### Step 2: Suggest a version number

Based on the commit audit, suggest a version number using semantic versioning:

- **PATCH** bump (e.g., 0.2.0 -> 0.2.1): only bug fixes, documentation, or internal changes
- **MINOR** bump (e.g., 0.2.0 -> 0.3.0): new features that don't break existing usage
- **MAJOR** bump (e.g., 0.2.0 -> 1.0.0): breaking changes that require users to change how they use the tool

If the user provided a version as an argument to `/release`, use that as the suggestion instead of deriving one.

Present to the user:

- Current version: `<current>`
- Suggested version: `<suggested>`
- Why: brief explanation of the reasoning
- Summary of the categorized changes from Step 1

Ask the user to confirm the suggested version or provide a different one. Do not proceed until the user has confirmed a version number.

### Step 3: Validate the version number

Once confirmed:

- Confirm it is a valid semver version (MAJOR.MINOR.PATCH)
- Check that it is greater than the current version
- Check that a git tag `v<version>` does not already exist

### Step 4: Check the README

- Review the commits from Step 1 for any user-facing changes
- Read `README.md` and check whether those changes are reflected
- If the README needs updating, show the user what you'd change and ask for confirmation
- Update `README.md` if the user approves

### Step 5: Check for uncommitted changes

- Run `git status` to check for unstaged or uncommitted changes
- If there are changes, list them and ask the user whether to include them in the release commit or leave them out
- Pay special attention to files like `uv.lock` that may have drifted

### Step 6: Stamp the release

Once everything is verified and complete:

1. Bump `version` in `pyproject.toml` to the new version
2. Stage all release-related files and commit with message: `Release v<version>`
3. Push to main

### Step 7: Create the GitHub release

- Write release notes summarizing the changes from Step 1
- Create the release: `gh release create v<version> --title "v<version>" --notes "<release notes>"`
- Watch the publish workflow to confirm it succeeds: find the run with `gh run list --workflow=publish.yml --limit=1` then `gh run watch <id>`
- Report the PyPI publish result to the user

### Step 8: Verify

- Confirm the release tag exists: `git tag --list "v<version>"`
- Report the release URL and PyPI package URL
