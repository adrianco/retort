# Setting up Gas Town to build Retort

## What's what

- **Gas Town** — Steve Yegge's multi-agent coding orchestrator (`gt` CLI, Mayor, Polecats, etc.)
- **Retort** (`adrianco/retort`) — a project rig under Gas Town management, implementing a statistical DoE engine for developer platform evolution

The Mayor builds Retort. The plan document is the Mayor's brief.

---

## Step 1: Install Gas Town in the Codespace

```bash
# Option A: npm
npm install -g @gastown/gt

# Option B: Homebrew
brew install gastown

# Option C: From source
go install github.com/steveyegge/gastown/cmd/gt@latest
export PATH="$PATH:$HOME/go/bin"
```

## Step 2: Install Beads

```bash
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
```

## Step 3: Initialize your town

```bash
gt install ~/gt --git
cd ~/gt
```

## Step 4: Add Retort as a rig

```bash
gt rig add retort https://github.com/adrianco/retort.git
```

## Step 5: Set up your crew workspace

```bash
gt crew add adrian --rig retort
cd retort/crew/adrian
```

## Step 6: Put the plan where the Mayor can find it

Copy the plan document into the retort repo so the Mayor has the full spec:

```bash
mkdir -p docs
# Copy platform-evolution-engine-plan.md into docs/plan.md
# Copy retort-logo.svg into assets/
```

Also initialize Beads for task tracking:

```bash
bd init
```

## Step 7: Start the Mayor and brief it

```bash
gt mayor attach
```

Then give the Mayor the brief:

```
Read docs/plan.md — this is the specification for Retort, a Python 
package that applies statistical Design of Experiments to evaluate 
developer tooling stacks.

Build Phase 0 first:
1. pyproject.toml — PEP 621, hatch backend, CLI entry point `retort`
2. src/retort/ package with:
   - cli.py (click CLI: init, design generate, run, analyze, promote, intake, report)
   - config/schema.py (Pydantic models for workspace.yaml)
   - config/loader.py (YAML loading + validation)
   - design/factors.py (factor registry)
   - design/generator.py (fractional factorial via pyDOE3)
   - storage/models.py (SQLAlchemy/SQLite)
3. Tests that pass
4. `retort --help` works after `pip install -e ".[dev]"`

Use Python 3.12+, strict typing, ruff for linting. 
Keep it minimal and correct — no runners, scorers, or analysis yet.

Create beads for each deliverable so we can track progress.
```

---

## What happens next

The Mayor will coordinate the work — spawning Polecats to implement different modules, tracking progress via Beads, and managing the overall build. You stay in the Overseer role, reviewing PRs and steering.

The plan document has four phases. Feed them to the Mayor one at a time as each phase completes:

- **Phase 0** — Skeleton: config, design generation, CLI, storage
- **Phase 1** — Playpen + scoring: Docker runner, scorer plugins, bundled tasks
- **Phase 2** — Analysis + promotion: ANOVA, Bayesian updating, Pareto, lifecycle gates
- **Phase 3** — Continuous operation: candidate intake, D-optimal augmentation, budgeting, dashboard
