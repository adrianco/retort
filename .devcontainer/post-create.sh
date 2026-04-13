#!/usr/bin/env bash
#
# Provisioning for a fresh retort dev container.
#
# Steps:
#   1. Editable install of retort + dev/test extras
#   2. Install the `claude` CLI (LocalRunner shells out to it)
#   3. Install the `bd` (beads) CLI (needed when factor `tooling: beads` is used)
#   4. Pre-commit hooks if configured
#   5. Verify everything is on PATH and report what still needs the user's hand
#
# Per-language toolchains (node, go, rust) are provided by devcontainer features
# in devcontainer.json. They are only needed for languages you actually list as
# factor levels in workspace.yaml.

set -euo pipefail

step() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*" >&2; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }

step "Installing retort + dev/test extras (editable)"
pip install --no-cache-dir -e ".[dev,test]"

step "Installing claude CLI"
if command -v claude >/dev/null 2>&1; then
    ok "claude already installed: $(claude --version 2>&1 | head -1)"
else
    npm install -g @anthropic-ai/claude-code
    ok "claude installed — run 'claude' once interactively to authenticate"
fi

step "Installing bd (beads) CLI"
if command -v bd >/dev/null 2>&1; then
    ok "bd already installed: $(bd --version 2>&1 | head -1)"
else
    curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/install.sh | bash \
        || warn "bd install script failed — install manually from https://github.com/steveyegge/beads/releases if you need tooling=beads experiments"
fi

if [ -f .pre-commit-config.yaml ]; then
    step "Installing pre-commit hooks"
    pre-commit install
fi

step "Verifying prerequisites"
fail=0
check() {
    local name=$1
    local cmd=$2
    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$name: $($cmd --version 2>&1 | head -1)"
    else
        warn "$name MISSING — install before running experiments that use it"
        fail=1
    fi
}
check "python"  python
check "retort"  retort
check "claude"  claude
check "bd"      bd
check "node"    node      # for typescript factor levels
check "go"      go        # for go factor levels
check "rustc"   rustc     # for rust factor levels
check "cargo"   cargo     # for rust factor levels

if [ "$fail" -eq 0 ]; then
    ok "All prerequisites present."
else
    warn "Some prerequisites are missing. They are only required if your"
    warn "workspace.yaml lists the corresponding factor levels."
fi

step "Done"
echo "Next:"
echo "  1. Authenticate claude:    claude  (then exit)"
echo "  2. Init a workspace:       retort init my-eval"
echo "  3. Edit workspace.yaml, set 'runner: local' under playpen"
echo "  4. Run:                    retort run --phase screening --config workspace.yaml"
