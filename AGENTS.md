# AGENTS.md — skills-mcp

Standalone, agent-agnostic MCP server. **Bring your own agent; this brings
the skills (Anthropic Agent Skills / `SKILL.md`) + a bare-metal execution
surface.** No bundled agent, no identity of its own — deliberately.

## What it is

FastMCP server (v3, same framework as mneme's `tools-server`). Three jobs:
- **discovery** — `SkillsDirectoryProvider` (built in) + `list_skills`/`read_skill`
- **creation** — `create_skill` / `write_skill_file` (the "learn a skill live" beat)
- **execution** — `bash` (arbitrary shell; env inherits, so `$LIFX_TOKEN` etc. work)

## Layout

- `skills_mcp/__init__.py` — the whole server (~5 tools + provider).
- `skills/` — the skills repo (each subdir = a skill with a `SKILL.md`).
- `Dockerfile`, `railway.toml` — deploy. In prod, mount a volume at `/data`
  and set `SKILLS_DIR=/data/skills` so authored skills survive redeploys.

## Conventions

- No sandboxing by design — single-user, single-tenant box you control.
- Keep it tiny. Skills are files; the agent is the brain. Don't grow an
  agent/identity in here — that's the consumer's job (e.g. Spark).
- Conventional commits. Don't commit `.env` or `skills/` secrets.

## Consumers

Exposed to an LLM agent over MCP (HTTP or stdio), or behind the
`mcp-gateway` like the other device/capability MCPs (`imessage-mcp`,
`whatsapp-mcp`, ...). For mneme/Spark: the Woodward demo's Track E
("learn a skill live" → turn on a LIFX light). See
`~/prg/mneme/plans/040-woodward-demo.md` and
`~/prg/mneme/notes/lifx-light-runbook.md`.
