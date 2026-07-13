# How do we ship AGENTS.md with the uv tool install?
This is in the GitHub repo, but doesn't natively ship with the uv tool install, right?

# We need to provide guidance on using the Python SDK for automation
This exists solely for programming reuse of CDP browsing tasks / automation

# Refresh the typed protocol bindings (54 domains frozen; live Chrome serves 56)
src/chrome_agent/domains/ is a point-in-time snapshot generated 2026-04-13 and has drifted from current Chrome (missing e.g. CrashReportContext, WebMCP). This only affects the typed Python API's ergonomics -- the CLI and CDPClient.send() already track whatever the running browser supports. Decide: a simple regen via scripts/generate_bindings.py, or the larger "bundle a pinned upstream CDP JSON" idea so `help` also works offline and with 0 or many instances running.

# Land the reworked AGENTS.md from research/agents-md-enhancement/
Public (`research/agents-md-enhancement/AGENTS-public-rewrite.md`) + private (`AGENTS-private-delta-v3.md`) passed a full 3-stage adversarial review (re-run 2026-07-13); all must-fixes applied, no false claims. Before landing: (1) reconcile the "tracks the running browser, not its own version" note now in the live AGENTS.md; (2) add the README "public vs. project-specific manual" section (resolves the public doc's forward reference) during wiring; (3) restore the quantitative experimental-stability numbers -- softened to qualitative for now (Option B) -- once the analysis publishes with the AIE talk.

# Decide where the forensic-capture analysis lives
research/cdp-forensic-capture-capability-analysis.md refutes the "an agent can't script subresource capture" claim (empirically: Page.getResourceTree + getResourceContent, or the Network domain, capture subresources to a directory; MHTML omits JS). It's untracked -- commit it, relocate it, or leave it as a scratch note.

# Wire up the public/private AGENTS split
Create prompthub/browsing/chrome-agent.md (private real file); symlink chrome-agent/AGENTS-private.md -> it and gitignore it; repoint the @-import so agents load the PRIVATE layer (settle mechanic A vs B; verify nested @-import support); add the README public-vs-private section; swap the live AGENTS.md with the public rewrite. The private layer must NEVER be committed to the public repo -- its home is prompthub/browsing/.

# Annotate the refuted save-page-as learning record
~/Documents/99_learning-records/2026-04-28-save-page-as-complete-as-forensic-capture.md's "no CDP equivalent captures subresources" claim is refuted by research/cdp-forensic-capture-capability-analysis.md (Chrome 149): the agent CAN script capture -- Network.getResponseBody before the destructive action, or Page.getResourceTree + getResourceContent; MHTML omits <script>. Update the record in place.
