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


## Add auto-cleanup ... 

When agents land as "stopped", is there a way to restart them?  If not, then they should be automatically cleaned up ... 


## Write AGENTS.md / SKILLS to enable agents to fully use chrome-agent


