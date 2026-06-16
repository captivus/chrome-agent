# TODO

## Issues to address

Codex logged this issue today when trying to launch a visible window. Not sure why it has problems vs Claude Code.

```markdown
# Feedback: Chrome-Agent Visible Browser Keep-Alive

Date: 2026-05-24

## Incident

During Motomon UI QA, the user asked for a non-headless `chrome-agent` instance so the browser work would be visible. `chrome-agent launch --port 9333` reported success, but `chrome-agent status` immediately showed the instance as `"alive": false` with no targets.

## Rule

When visible browser QA is required and `chrome-agent launch` reports success but the instance immediately dies, do not fall back to headless mode. Start Chrome directly in a persistent shell session with `--remote-debugging-port`, keep that session alive, then register the CDP port for `chrome-agent` commands.

## Working Pattern

```bash
/usr/bin/google-chrome-stable \
  --remote-debugging-port=9333 \
  --user-data-dir=/tmp/chrome-agent/session-<task-name> \
  --no-first-run \
  --no-default-browser-check \
  --password-store=basic \
  <start-url>
```

Verify Chrome prints `DevTools listening on ws://127.0.0.1:<port>/devtools/browser/...`, then register the instance in `/tmp/chrome-agent/registry.json` so `chrome-agent status` reports `"alive": true`.

## Why

The user's requirement is observable QA in a visible browser. A one-shot launcher that leaves only a dead registry entry satisfies neither visibility nor controllability, even if it prints a success message.
```
```


## Add --version flag to CLI

There isn't one today, which is odd ... 


## Add auto-cleanup ... 

When agents land as "stopped", is there a way to restart them?  If not, then they should be automatically cleaned up ... 


## Write AGENTS.md / SKILLS to enable agents to fully use chrome-agent


## WebRTC leaks the real public IP (from detection audit, 2026-06-16)

`research/2026-06-16-detection-audit.md` found that all launch configs leak the
host's real public IP via WebRTC (CreepJS surfaced it directly), independent of
`--fingerprint`. This is the largest deanonymization vector for stealth use and
is not addressed today. Options to evaluate: a `--disable-features` flag, a
WebRTC IP-handling policy, or documenting it as a known limitation.

## fingerprint scope narrowed (done 2026-06-16)

`fingerprint.py` no longer injects navigator JS overrides (they were
net-negative for detection -- see the audit). It now spoofs UA / viewport /
language / timezone via launch flags only. `platform`/`vendor` profile fields
are retained for compatibility but no longer spoofed; revisit if a
non-detectable mechanism (e.g. UA-Client-Hints metadata) is wanted.
