# skills-mcp

Agent-agnostic MCP server for **Anthropic Agent Skills** (`SKILL.md`) on
bare metal. **Bring your own agent; this brings the skills + execution.**

It solves the three problems of a self-authoring skills layer, with no
bundled agent and no identity of its own:

| Problem | How |
|---|---|
| **Discovery** | FastMCP's built-in `SkillsDirectoryProvider` exposes every `skills/<name>/SKILL.md` as an MCP resource (`skill://<name>/SKILL.md`). `reload=True` makes new skills appear instantly. Plus `list_skills` / `read_skill` tools for tools-only clients. |
| **Creation** | `create_skill(name, skill_md)` writes a new `SKILL.md` — live on the next call. This is the "learn a skill live" beat. |
| **Execution** | `bash(command)` runs arbitrary shell on the box (apt, curl, python...). Skills are *instructions the agent runs*; the agent reads a SKILL.md, then executes it via `bash`. |

The box's environment inherits into `bash`, so secrets (e.g. `LIFX_TOKEN`)
set on the box are available to the commands skills run.

> No sandboxing. This is a bare-metal execution surface by design — run it
> as a single-user, single-tenant box you control.

## Tools

- `list_skills() -> [{name, description}]`
- `read_skill(name) -> str`
- `create_skill(name, skill_md) -> uri`
- `write_skill_file(name, relpath, content) -> path`
- `bash(command, timeout=120) -> str`

Plus MCP **resources** via the Skills Provider: `skill://<name>/SKILL.md`,
`skill://<name>/_manifest`, and supporting files.

## Run

```bash
uv sync
# HTTP (default; for Railway / remote agents)
PORT=8000 uv run skills-mcp
# or stdio (local agent)
MCP_TRANSPORT=stdio uv run skills-mcp
```

Env:
- `SKILLS_DIR` — where skills live (default `./skills`).
- `MCP_TRANSPORT` — `http` (default) or `stdio`.
- `PORT` / `HOST` — HTTP bind (default `0.0.0.0:8000`).
- any secrets your skills need (e.g. `LIFX_TOKEN`).

## The "learn a skill live" loop

1. Agent: `list_skills()` → gap (no `lifx-control`).
2. Agent: `create_skill("lifx-control", "<SKILL.md with the curl>")`.
3. Agent: `bash('curl -X PUT https://api.lifx.com/v1/lights/all/state -H "Authorization: Bearer $LIFX_TOKEN" -d power=on')`.
4. Light turns on. The agent (e.g. Spark) is the only brain — no second
   agent, no injected identity.

## Skill format

A skill is a directory with a `SKILL.md` (Anthropic Agent Skills open
standard). Optional YAML frontmatter `description:`; optional supporting
files. See `skills/hello/`.
