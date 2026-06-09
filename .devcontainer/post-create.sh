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
# Per-language toolchains: node, go, rust, and java(+maven) are provided by
# devcontainer features in devcontainer.json. The BEAM + Clojure tools (erlang,
# elixir, rebar3, clojure CLI, leiningen, clj-kondo) have no reliable feature,
# so they are installed best-effort below. All are only needed for languages you
# actually list as factor levels in workspace.yaml.

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

step "Installing BEAM + Clojure toolchains (erlang, elixir, rebar3, clojure, lein, clj-kondo)"
# Best-effort: a failure here only matters if you run that language. apt covers
# the Debian base image; the rest are single-binary installers.
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq \
        && sudo apt-get install -y --no-install-recommends \
            erlang elixir rebar3 leiningen \
        || warn "apt install of erlang/elixir/rebar3/leiningen partially failed — install manually if you use those languages"
fi
# Clojure CLI (clj/clojure) — not in apt; use the official installer.
if ! command -v clojure >/dev/null 2>&1; then
    curl -fsSL https://github.com/clojure/brew-install/releases/latest/download/linux-install.sh -o /tmp/clj-install.sh \
        && sudo bash /tmp/clj-install.sh \
        || warn "clojure CLI install failed — see https://clojure.org/guides/install_clojure"
fi
# clj-kondo (defect_rate linter for clojure).
if ! command -v clj-kondo >/dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/clj-kondo/clj-kondo/master/script/install-clj-kondo -o /tmp/install-clj-kondo \
        && sudo bash /tmp/install-clj-kondo \
        || warn "clj-kondo install failed — see https://github.com/clj-kondo/clj-kondo/blob/master/doc/install.md"
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
check "python"   python
check "retort"   retort
check "claude"   claude
check "bd"       bd
# Per-language build/test/lint tools the scorer shells out to. Each is only
# needed if you list that language as a factor level in workspace.yaml.
check "node"     node      # typescript: jest/vitest, tsc, eslint (via npx)
check "go"       go        # go: go test -cover, go vet
check "cargo"    cargo     # rust: cargo test, cargo clippy
check "java"     java      # java + clojure + BEAM all need a JDK on PATH
check "mvn"      mvn       # java: mvn test, jacoco
check "clojure"  clojure   # clojure: deps.edn projects (clojure -M:test, cloverage)
check "lein"     lein      # clojure: leiningen (project.clj) projects — BOTH needed
check "clj-kondo" clj-kondo # clojure: defect_rate linter
check "erl"      erl       # erlang/elixir runtime (BEAM)
check "rebar3"   rebar3    # erlang: rebar3 eunit / rebar3 ct
check "elixir"   elixir    # elixir: mix test
check "mix"      mix       # elixir: ships with elixir

if [ "$fail" -eq 0 ]; then
    ok "All prerequisites present."
else
    warn "Some prerequisites are missing. They are only required if your"
    warn "workspace.yaml lists the corresponding factor levels. A missing"
    warn "build tool makes every run of that language fail its tests-gate."
fi

step "Done"
echo "Next:"
echo "  1. Authenticate claude:    claude  (then exit)"
echo "  2. Init a workspace:       retort init my-eval"
echo "  3. Edit workspace.yaml, set 'runner: local' under playpen"
echo "  4. Run:                    retort run --phase screening --config workspace.yaml"
