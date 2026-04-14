# Protocol Schema Sources for Code Generation

## Question

Where does the CDP protocol specification come from, and is it machine-readable enough for code generation?

The GEN-01 feature needs to generate typed Python bindings for every CDP domain, command, event, and type. This requires a structured, complete protocol definition as input. Before specifying the generator, we need to understand what source formats exist and which one is the right input.

## Sources Discovered

Two authoritative sources exist for the CDP protocol definition.

### Source A: Chrome's `/json/protocol` HTTP endpoint

Any running Chrome (or Chromium-based) browser with remote debugging enabled serves its complete protocol schema as structured JSON at the `/json/protocol` endpoint. This is the same schema that DevTools itself uses internally.

**How it was tested:**

```
curl http://localhost:9222/json/protocol
```

The response is a single JSON object with a top-level `domains` array. Each domain contains `commands`, `events`, and `types` arrays. Examining the `Page.navigate` command in the output confirmed full detail:

- **Parameters** include `name`, `type`, `description`, and an `optional` flag for each parameter
- **Return values** are specified with the same structure as parameters
- **Events** include their parameter definitions
- **Types** include property definitions, enum values, and descriptions
- **Domain metadata** includes `experimental` and `deprecated` flags, dependency declarations, and domain descriptions

The JSON is immediately usable -- no parsing or transformation layer is needed beyond standard JSON deserialization.

### Source B: PDL files in the devtools-protocol repository

The [devtools-protocol](https://github.com/AmanVirmani/devtools-protocol) GitHub repository contains the canonical protocol definition in Protocol Definition Language (PDL) files. The entry point is `browser_protocol.pdl`, which includes individual domain files:

```
version
  major 1
  minor 3

include domains/Accessibility.pdl
include domains/Animation.pdl
include domains/Audits.pdl
...
```

Each domain file (e.g., `domains/Page.pdl`) defines types, commands, and events using an indentation-based DSL:

```
domain Page
  depends on Debugger
  depends on DOM
  depends on IO
  depends on Network
  depends on Runtime

  type FrameId extends string

  experimental type AdFrameType extends string
    enum
      none
      child
      root
```

The repository contains 50 domain PDL files. The format is human-readable and machine-parseable, but requires a custom PDL parser -- there is no standard library for this format.

## Analysis

| Criterion | `/json/protocol` endpoint | PDL files |
|---|---|---|
| Format | Structured JSON | Custom DSL (PDL) |
| Parser needed | `json.loads()` | Custom PDL parser |
| Version accuracy | Always matches connected browser | Matches repository revision |
| Availability | Requires running browser | Static files, always available |
| Coverage | Complete (50 domains, ~518 commands and events) | Complete (50 domain files) |
| Descriptions included | Yes | Yes |
| Types/enums included | Yes | Yes |

## Conclusion

**The `/json/protocol` JSON endpoint is the right input for code generation.** Three factors make it the clear choice:

1. **No custom parser needed.** The JSON is already structured data. PDL would require writing and maintaining a parser for a format with no public specification beyond the files themselves.

2. **Version-matched by construction.** The endpoint returns the protocol for the exact browser version it's running on. There is no risk of version skew between the schema and the browser the generated bindings will be used against.

3. **Complete and self-contained.** A single HTTP request returns every domain, command, event, type, parameter, return value, and description. No file assembly or include resolution required.

PDL files are deferred as an alternative input source. They could be useful if offline generation (without a running browser) becomes a requirement, but that would require building a PDL parser -- unnecessary complexity for the initial implementation.

## Cross-references

- [GEN-01 spec](../GEN-01-typed-protocol-bindings.md) -- uses the `/json/protocol` endpoint as the generator's input source (Implementation Contract Level 2, INPUT section)
