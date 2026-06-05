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

# Skills live on a persistent volume in prod so authored skills survive
# redeploys. Mount a Railway volume at /data and set SKILLS_DIR=/data/skills.
ENV SKILLS_DIR=/data/skills
ENV MCP_TRANSPORT=http
ENV PORT=8000
EXPOSE 8000

CMD ["uv", "run", "skills-mcp"]
