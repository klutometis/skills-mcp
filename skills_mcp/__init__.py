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

Env does NOT blanket-inherit into `bash`. Commands get a minimal base env
plus whatever `SKILLS_ENV_PASSTHROUGH` names explicitly (e.g. LIFX_TOKEN),
so an agent running `env` can't scrape unrelated platform credentials into
a transcript.

Multi-tenancy
-------------
Single-tenant by default: one skills dir, no auth (the personal-stack
shape, reached only over railway.internal).

Set ``SKILLS_GATEWAY_TOKEN`` to run multi-tenant behind a trusted gateway.
Then every request must carry that bearer token, and the caller's identity
arrives as W3C ``baggage`` (default key ``userId``) which the gateway
stamped from the authenticated human. Each tenant gets its own
``$SKILLS_DIR/<userId>`` -- skills, supporting files and the `bash` cwd are
all scoped to it. Same trust model as whatsapp-mcp: the gateway is the
boundary, upstreams are not publicly reachable, baggage carries an opaque
id and never a secret.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from urllib.parse import unquote

import secrets

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.providers.skills import SkillsDirectoryProvider

SKILLS_DIR = Path(
    os.environ.get("SKILLS_DIR")
    or (Path(__file__).resolve().parent.parent / "skills")
).resolve()
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

# Multi-tenant when a gateway token is configured; single-tenant otherwise.
GATEWAY_TOKEN = os.environ.get("SKILLS_GATEWAY_TOKEN", "").strip()
BAGGAGE_KEY = os.environ.get("SKILLS_BAGGAGE_KEY", "userId").strip() or "userId"
MULTITENANT = bool(GATEWAY_TOKEN)

# Names allowed through into `bash`, on top of the minimal base env below.
ENV_PASSTHROUGH = [
    n.strip()
    for n in os.environ.get("SKILLS_ENV_PASSTHROUGH", "LIFX_TOKEN").split(",")
    if n.strip()
]

mcp = FastMCP("skills-mcp")

# --- discovery (built-in): each skills/<name>/SKILL.md -> MCP resource ---
# reload=True re-scans on every request, so a freshly-authored skill is
# visible immediately (the hot-reload that makes "learn a skill live" work).
#
# Only mounted single-tenant. The provider takes a static root at import
# time, so under multi-tenancy it would publish every tenant's skills to
# every caller as MCP resources. Tools below are per-request and stay
# scoped; tools-only is also how the gateway consumes this server.
if not MULTITENANT:
    mcp.add_provider(SkillsDirectoryProvider(roots=SKILLS_DIR, reload=True))


def _baggage_value(headers: dict[str, str], key: str) -> str:
    """Extract one key from the W3C `baggage` header, percent-decoded,
    ignoring any ;properties on the member."""
    for member in headers.get("baggage", "").split(","):
        k, _, v = member.strip().partition("=")
        if k.strip() != key:
            continue
        v = v.split(";", 1)[0].strip()
        return unquote(v)
    return ""


def _skills_dir() -> Path:
    """Resolve (and create) the caller's skills directory.

    Single-tenant: the configured SKILLS_DIR, no auth.

    Multi-tenant: require the gateway bearer token, then derive the tenant
    from baggage. Fails closed -- a missing/wrong token or a missing
    identity raises rather than falling back to the shared root, so a
    misconfigured gateway cannot silently hand one tenant another's skills.
    """
    if not MULTITENANT:
        return SKILLS_DIR

    # get_http_headers() strips `authorization` by default (it exists to
    # build safe downstream calls). We need it, so ask for it explicitly.
    headers = get_http_headers(include={"authorization"})
    auth = headers.get("authorization", "")
    token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
    if not token or not secrets.compare_digest(token, GATEWAY_TOKEN):
        raise PermissionError("missing or invalid gateway token")

    raw = _baggage_value(headers, BAGGAGE_KEY)
    if not raw:
        raise PermissionError(f"no {BAGGAGE_KEY} in baggage; cannot resolve tenant")

    # Same sanitizer the gateway's "safe" mode uses, applied again here:
    # never trust an upstream to have slugified before we join a path.
    tenant = re.sub(r"[^a-zA-Z0-9_-]", "-", raw)[:128].strip("-")
    if not tenant:
        raise PermissionError("empty tenant id after sanitisation")

    d = (SKILLS_DIR / tenant).resolve()
    if d.parent != SKILLS_DIR:
        raise PermissionError("tenant id escapes skills root")
    d.mkdir(parents=True, exist_ok=True)
    return d


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
def list_skills() -> str:
    """List available skills with their one-line descriptions (JSON array of
    {name, description}). Returns '[]' when there are no skills yet."""
    root = _skills_dir()
    out = []
    for d in sorted(root.iterdir()) if root.exists() else []:
        sm = d / "SKILL.md"
        if d.is_dir() and sm.exists():
            out.append({"name": d.name, "description": _description(sm)})
    return json.dumps(out)


@mcp.tool
def read_skill(name: str) -> str:
    """Return the full SKILL.md for a skill (the instructions to follow)."""
    sm = _skills_dir() / _safe_name(name) / "SKILL.md"
    if not sm.exists():
        raise FileNotFoundError(f"no skill named {name!r}")
    return sm.read_text(encoding="utf-8")


# --- creation ("learn a skill live") ---
@mcp.tool
def create_skill(name: str, skill_md: str) -> str:
    """Author a new skill. `skill_md` is the full SKILL.md content (ideally
    with YAML frontmatter `--- description: ... ---`). Available immediately."""
    d = _skills_dir() / _safe_name(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return f"skill://{d.name}/SKILL.md"


@mcp.tool
def delete_skill(name: str) -> str:
    """Delete a skill (its whole directory). Use to reset / clean up, e.g. to
    rehearse the 'learn a skill live' loop from a clean slate."""
    d = _skills_dir() / _safe_name(name)
    if not d.exists():
        raise FileNotFoundError(f"no skill named {name!r}")
    shutil.rmtree(d)
    return f"deleted {name}"


@mcp.tool
def write_skill_file(name: str, relpath: str, content: str) -> str:
    """Write a supporting file inside a skill directory (scripts, refs, etc.)."""
    base = _skills_dir() / _safe_name(name)
    target = (base / relpath).resolve()
    if base.resolve() not in target.parents and target != base.resolve():
        raise ValueError("path escapes skill directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target)


# --- execution ---
def _bash_env(cwd: Path) -> dict[str, str]:
    """Minimal base env plus explicitly-allowed passthroughs.

    Deliberately not os.environ.copy(): the agent decides what to run, and
    `env`/`printenv` output lands in a transcript. Only names in
    SKILLS_ENV_PASSTHROUGH cross over.
    """
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(cwd),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "SKILLS_DIR": str(cwd),
    }
    for name in ENV_PASSTHROUGH:
        if (val := os.environ.get(name)) is not None:
            env[name] = val
    return env


@mcp.tool
def bash(command: str, timeout: int = 120) -> str:
    """Run a shell command on the box (apt, curl, python, ...). Runs in your
    own skills directory. Secrets the box is configured to share (e.g.
    $LIFX_TOKEN) are in scope. Returns stdout+stderr."""
    cwd = _skills_dir()
    r = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd),
        env=_bash_env(cwd),
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
