#!/bin/sh
# Prepare the skills dir, then drop to the unprivileged `skills` user.
#
# The volume mounts root-owned, so chown has to happen at runtime (a
# build-time chown would apply to the image layer, not the mount). After
# that nothing needs root: `bash` runs agent-authored commands, and those
# should not be able to write /etc or apt-get install.
set -eu

: "${SKILLS_DIR:=/data/skills}"

mkdir -p "$SKILLS_DIR"
chown -R 1000:1000 "$SKILLS_DIR" 2>/dev/null || true

# Seed the bundled sample skills on first boot (empty volume), so a fresh
# deploy isn't a blank slate. Never overwrites what a tenant has authored.
if [ -d /app/skills ] && [ -z "$(ls -A "$SKILLS_DIR" 2>/dev/null)" ]; then
    cp -r /app/skills/. "$SKILLS_DIR"/ 2>/dev/null || true
    chown -R 1000:1000 "$SKILLS_DIR" 2>/dev/null || true
fi

# setpriv keeps the current environment, so HOME would still be /root --
# unwritable once we drop privileges, which breaks anything that caches
# under it. Point it at the skills user's own home.
export HOME=/home/skills

exec setpriv --reuid=1000 --regid=1000 --clear-groups "$@"
