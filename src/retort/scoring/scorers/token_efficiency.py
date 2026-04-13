"""Token efficiency scorer.

Measures how efficiently the agent used tokens relative to the
amount of functional output produced.
"""

from __future__ import annotations

from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig

# Rough target: lines of code per 1000 tokens
# Higher is better — agent produced more code per token spent
TARGET_LINES_PER_KTOKEN = 50.0


class TokenEfficiencyScorer:
    """Scores token efficiency: functional output per token consumed.

    Score range: 0.0 (worst) to 1.0 (best).
    A score of 1.0 means the agent achieved the target efficiency or better.
    """

    @property
    def name(self) -> str:
        return "token_efficiency"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        # Score regardless of exit_code — see CodeQualityScorer for rationale.
        tokens = artifacts.token_count
        if tokens <= 0:
            # No token data — estimate from output length
            tokens = self._estimate_tokens(artifacts)
            if tokens <= 0:
                return 0.5  # Can't measure, neutral score

        lines = self._count_output_lines(artifacts, stack.language)
        if lines == 0:
            return 0.0

        lines_per_ktoken = (lines / tokens) * 1000
        # Normalize to 0-1 scale against target
        return min(1.0, lines_per_ktoken / TARGET_LINES_PER_KTOKEN)

    def _count_output_lines(self, artifacts: RunArtifacts, language: str) -> int:
        """Count lines of source code produced."""
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0

        extensions = {
            "python": {".py"},
            "typescript": {".ts", ".tsx", ".js", ".jsx"},
            "go": {".go"},
            "rust": {".rs"},
            "java": {".java"},
            "clojure": {".clj", ".cljc", ".cljs"},
        }
        exts = extensions.get(language, {".py"})

        total = 0
        for ext in exts:
            for f in artifacts.output_dir.rglob(f"*{ext}"):
                try:
                    content = f.read_text()
                    # Count non-blank, non-comment lines
                    for line in content.splitlines():
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
                            total += 1
                except OSError:
                    pass
        return total

    @staticmethod
    def _estimate_tokens(artifacts: RunArtifacts) -> int:
        """Rough token estimate from stdout length."""
        text_len = len(artifacts.stdout) + len(artifacts.stderr)
        return text_len // 4  # ~4 chars per token approximation
