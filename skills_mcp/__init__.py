"""skills-mcp — Agent Skills (SKILL.md) over MCP, on bare metal.

Three primitives, agent-agnostic ("bring your own agent"):

- discovery  : SkillsDirectoryProvider (built into FastMCP) exposes every
               skills/<name>/SKILL.md as an MCP resource, plus `list_skills`
               / `read_skill` tools for tools-only clients.
- creation   : `create_skill(name, skill_md)` writes skills/<name>/SKILL.md
               (live next call via reload=True). This is the "learn a skill
               live" beat.
- execution  : `bash(command)` runs arbitrary shell on the box (apt, curl,
               python, ...). Skills are *instructions the agent runs*; the
               agent reads a SKILL.md then executes it via `bash`.

Env inherits into `bash`, so secrets like LIFX_TOKEN set on the box are
available to the commands skills run.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

SKILLS_DIR = Path(
    os.environ.get("SKILLS_DIR")
    or (Path(__file__).resolve().parent.parent / "skills")
).resolve()
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("skills-mcp")

# --- discovery (built-in): each skills/<name>/SKILL.md -> MCP resource ---
# reload=True re-scans on every request, so a freshly-authored skill is
# visible immediately (the hot-reload that makes "learn a skill live" work).
mcp.add_provider(SkillsDirectoryProvider(roots=SKILLS_DIR, reload=True))


def _safe_name(name: str) -> str:
    """Slugify a skill name; no path traversal."""
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip()).strip("-._")
    if not slug:
        raise ValueError("invalid skill name")
    return slug


def _description(skill_md: Path) -> str:
    """Pull a one-line description: YAML frontmatter `description:` or first
    meaningful line of the body."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            front = text[3:end]
            m = re.search(r"^\s*description:\s*(.+)$", front, re.MULTILINE)
            if m:
                return m.group(1).strip().strip("\"'")
            text = text[end + 4 :]
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if s:
            return s
    return ""


# --- discovery (tools, for tools-only clients) ---
@mcp.tool
def list_skills() -> list[dict]:
    """List available skills with their one-line descriptions."""
    out = []
    for d in sorted(SKILLS_DIR.iterdir()) if SKILLS_DIR.exists() else []:
        sm = d / "SKILL.md"
        if d.is_dir() and sm.exists():
            out.append({"name": d.name, "description": _description(sm)})
    return out


@mcp.tool
def read_skill(name: str) -> str:
    """Return the full SKILL.md for a skill (the instructions to follow)."""
    sm = SKILLS_DIR / _safe_name(name) / "SKILL.md"
    if not sm.exists():
        raise FileNotFoundError(f"no skill named {name!r}")
    return sm.read_text(encoding="utf-8")


# --- creation ("learn a skill live") ---
@mcp.tool
def create_skill(name: str, skill_md: str) -> str:
    """Author a new skill. `skill_md` is the full SKILL.md content (ideally
    with YAML frontmatter `--- description: ... ---`). Available immediately."""
    d = SKILLS_DIR / _safe_name(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return f"skill://{d.name}/SKILL.md"


@mcp.tool
def write_skill_file(name: str, relpath: str, content: str) -> str:
    """Write a supporting file inside a skill directory (scripts, refs, etc.)."""
    base = SKILLS_DIR / _safe_name(name)
    target = (base / relpath).resolve()
    if base.resolve() not in target.parents and target != base.resolve():
        raise ValueError("path escapes skill directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target)


# --- execution ---
@mcp.tool
def bash(command: str, timeout: int = 120) -> str:
    """Run a shell command on the box (apt, curl, python, ...). Inherits the
    box env, so secrets like $LIFX_TOKEN are available. Returns stdout+stderr."""
    r = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(SKILLS_DIR),
        env=os.environ.copy(),
    )
    body = (r.stdout or "") + (r.stderr or "")
    return f"exit={r.returncode}\n{body}".strip()


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "http")
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(
            transport="http",
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8000")),
        )


if __name__ == "__main__":
    main()
