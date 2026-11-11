#!/bin/bash
set -uo pipefail

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

log() { echo "session-start: $*" >&2; }

# config.env sits at the root of the clone this hook lives in: this file is in
# MEMORY_REPO because the config is, the same two directories up as the sweep
# reads it from, so there is nothing to search for. AGENTS_CONFIG overrides.
config="${AGENTS_CONFIG:-$(cd "$(dirname "$0")/../.." && pwd)/config.env}"
if [ -r "$config" ]; then
  agent="$(sed -n 's/^AGENT=//p' "$config" | tail -1)"
  agent_email="$(sed -n 's/^AGENT_EMAIL=//p' "$config" | tail -1)"
else
  agent="" agent_email=""
fi
if [ -n "$agent" ] && [ -n "$agent_email" ]; then
  git config --global --replace-all user.name "$agent"
  git config --global --replace-all user.email "$agent_email"
  log "git identity: $(git config --global user.name) <$(git config --global user.email)> (from $config)"
else
  if [ ! -r "$config" ]; then
    log "config.env is unreadable: $config"
  else
    [ -n "$agent" ] || log "config.env sets no AGENT"
    [ -n "$agent_email" ] || log "config.env sets no AGENT_EMAIL"
  fi
  cleared=yes
  for key in user.name user.email; do
    git config --global --unset-all "$key"
    case $? in 0 | 5) ;; *) cleared=no ;; esac
  done
  log "git identity NOT set (see above) — fix config.env before committing"
  [ "$cleared" = yes ] || log "could NOT clear the global identity: commits may" \
    "still be authored as $(git config --global user.name)" \
    "<$(git config --global user.email)> — clear it by hand"
fi

pkgs=()
command -v jq >/dev/null 2>&1 || pkgs+=(jq)
command -v gh >/dev/null 2>&1 || pkgs+=(gh)
[ -n "${AGENTS_SIGNING_KEY:-}" ] && ! command -v ssh-keygen >/dev/null 2>&1 && pkgs+=(openssh-client)

if [ ${#pkgs[@]} -gt 0 ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null 2>&1 || true
  if apt-get install -y -qq "${pkgs[@]}" >/dev/null 2>&1; then
    log "installed: ${pkgs[*]}"
  else
    log "apt install failed for: ${pkgs[*]} — the GitHub MCP tools remain available"
  fi
fi

[ -n "${GH_TOKEN:-}${GITHUB_TOKEN:-}" ] || log "note: no GH_TOKEN/GITHUB_TOKEN in env — gh will be unauthenticated"

command -v gh >/dev/null 2>&1 && log "$(gh --version | head -1)" || true

cleared=yes
for key in commit.gpgsign user.signingkey gpg.format gpg.ssh.program; do
  git config --global --unset-all "$key" 2>/dev/null
  case $? in 0 | 5) ;; *) cleared=no ;; esac
done
[ "$cleared" = yes ] || log "could NOT clear the signing config — commits may sign through stale settings"
if [ -n "${AGENTS_SIGNING_KEY:-}" ] && ! command -v ssh-keygen >/dev/null 2>&1; then
  log "AGENTS_SIGNING_KEY set but ssh-keygen unavailable — commits stay unsigned"
elif [ -n "${AGENTS_SIGNING_KEY:-}" ]; then
  key="$HOME/.ssh/agents_signing"
  mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
  printf '%s\n' "$AGENTS_SIGNING_KEY" > "$key"
  chmod 600 "$key"
  if ssh-keygen -y -P '' -f "$key" > "$key.pub" 2>/dev/null; then
    git config --global gpg.format ssh
    # the environment ships a global gpg.ssh.program of its own — pin ours
    git config --global --replace-all gpg.ssh.program ssh-keygen
    git config --global user.signingkey "$key"
    git config --global commit.gpgsign true
    log "commit signing on ($(ssh-keygen -lf "$key.pub" | awk '{print $2}'))"
  else
    rm -f "$key" "$key.pub"
    log "AGENTS_SIGNING_KEY is not a valid passphrase-free SSH key — commits stay unsigned"
  fi
else
  log "no AGENTS_SIGNING_KEY in env — commits stay unsigned"
fi

# Timed self check-ins: denied here per AGENTS.md, see CHANGELOG.md for why.
deny='["mcp__claude-code-remote__send_later","mcp__claude-code-remote__create_trigger","mcp__claude-code-remote__update_trigger","mcp__claude-code-remote__fire_trigger","ScheduleWakeup","CronCreate"]'
settings="$HOME/.claude/settings.json"
mkdir -p "$HOME/.claude"
[ -s "$settings" ] || echo '{}' > "$settings"
if jq --argjson deny "$deny" '.permissions.deny = ((.permissions.deny // []) + $deny | unique)' \
    "$settings" > "$settings.tmp" 2>/dev/null && mv "$settings.tmp" "$settings"; then
  log "timed check-ins denied: $(jq -c '.permissions.deny' "$settings")"
else
  rm -f "$settings.tmp"
  log "could NOT write the check-in deny to $settings — timed check-ins are NOT blocked"
fi

exit 0
