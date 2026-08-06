FROM python:3.13-slim

# Bare-metal execution surface for skills: give it the usual tools skills
# reach for (curl, git, jq, ca-certs). Add more at runtime via `bash`/apt.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
COPY skills_mcp ./skills_mcp
COPY skills ./skills
RUN uv sync

# `bash` runs agent-authored commands, so don't run them as root. The
# container is the sandbox; this just removes the free privilege escalation
# inside it (writing /etc, apt-get install, reading root-owned paths).
# uid 1000 must own the volume mount too -- see the chown in the entrypoint.
RUN useradd -m -u 1000 skills

# Skills live on a persistent volume in prod so authored skills survive
# redeploys. Mount a Railway volume at /data and set SKILLS_DIR=/data/skills.
ENV SKILLS_DIR=/data/skills
ENV MCP_TRANSPORT=http
ENV PORT=8000
EXPOSE 8000

# The Railway volume mounts as root-owned, so chown it before dropping
# privileges. Runs as root only for that one step.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uv", "run", "skills-mcp"]
