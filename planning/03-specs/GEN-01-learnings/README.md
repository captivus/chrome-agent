# GEN-01 Learnings: Typed Protocol Bindings

Exploratory research captured during specification of GEN-01 (Typed Protocol Bindings).

| # | Topic | Format | Summary |
|---|-------|--------|---------|
| 01 | [Protocol Schema Sources](01-protocol-schema-sources.md) | Plain markdown | Chrome serves its complete CDP protocol as structured JSON at `/json/protocol`. The PDL files in the devtools-protocol repository are the canonical source but require a custom parser. The JSON endpoint is the right input for code generation -- no parser needed, always version-matched, and complete in a single request. |
