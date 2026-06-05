---
description: Sanity-check skill — prints a greeting via bash. Format reference for new skills.
---

# Hello

A trivial example skill, also the canonical shape for new ones.

## When to use
- To verify the skills round-trip (discover -> read -> execute) works.

## Procedure
1. Run: `echo "hello from skills-mcp"`
2. Report the output back to the user.

## Notes
A "skill" is just this folder + SKILL.md. The agent reads these
instructions, then executes them with the `bash` tool. Secrets set on the
box (e.g. `$LIFX_TOKEN`) are available inside `bash`.
