"""Idiomatic-code scorer.

LLM-as-judge for adherence to language conventions. The plan calls this
out as one of the seven Phase-1 scorers; it's the only one that can't be
done by static analysis alone — judging "idiomatic" requires a model that
has read a lot of {language} code.

Design notes:

- Uses the cheapest available model (default: claude-haiku) — one short
  call per run keeps the cost on the order of $0.001/run.
- Caches the result in the run's output_dir as `.idiomatic_cache.json`,
  so re-scoring (re-evaluation, dashboards) is free.
- Falls back to a neutral 0.5 on any error: missing CLI, parse failure,
  network blip. Never raises into the run loop.
- Sends a small *representative* sample of the code (capped at 4 KB),
  not the whole project, to keep latency and cost predictable.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig


logger = logging.getLogger(__name__)


# Default model name for the judge. Override via the IDIOMATIC_JUDGE_MODEL env
# var or by registering a custom IdiomaticScorer instance.
DEFAULT_JUDGE_MODEL = "haiku"

_LANGUAGE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "typescript": {".ts", ".tsx"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
    "clojure": {".clj", ".cljc", ".cljs"},
}

_SKIP_PARTS = {"node_modules", "target", "__pycache__", ".git", "dist", "build"}

# Cap the prompt body to keep latency + cost bounded. 4 KB is plenty for a
# representative sample without sending an entire project.
_SAMPLE_BUDGET_CHARS = 4096

_SCORE_RE = re.compile(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b")


class IdiomaticScorer:
    """LLM-as-judge scorer for language-idiom adherence.

    Score range: 0.0 (unidiomatic / non-conventional) to 1.0 (idiomatic).
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        cli: str = "claude",
        timeout_seconds: int = 60,
    ) -> None:
        import os
        self.model = model or os.environ.get("IDIOMATIC_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
        self.cli = cli
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "idiomatic"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        if not artifacts.succeeded:
            return 0.0
        if artifacts.output_dir is None or not artifacts.output_dir.exists():
            return 0.0

        # Cache lookup — re-scoring is free.
        cache_file = artifacts.output_dir / ".idiomatic_cache.json"
        if cache_file.exists():
            cached = _load_cache(cache_file)
            if cached is not None:
                return cached

        sample = _representative_sample(artifacts.output_dir, stack.language)
        if not sample:
            return 0.0

        score = self._judge(sample, stack.language)
        if score is None:
            return 0.5
        _write_cache(cache_file, score, self.model)
        return score

    def _judge(self, sample: str, language: str) -> float | None:
        prompt = (
            f"You are a senior {language} engineer reviewing code for "
            f"idiomatic adherence to {language} conventions (style, naming, "
            f"error handling, structure, common patterns).\n\n"
            f"Rate the following {language} code on a single scale from "
            f"0.0 (unidiomatic) to 1.0 (idiomatic).\n\n"
            f"Output ONLY a single decimal number, nothing else. No explanation, "
            f"no markdown, no prose. Just the number.\n\n"
            f"```{language}\n{sample}\n```"
        )

        try:
            result = subprocess.run(
                [
                    self.cli,
                    "-p", prompt,
                    "--model", self.model,
                    "--max-turns", "1",
                    "--output-format", "text",
                    "--dangerously-skip-permissions",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.info("idiomatic judge unavailable: %s", exc)
            return None

        return _parse_score(result.stdout)


def _representative_sample(root: Path, language: str) -> str:
    """Concatenate up to _SAMPLE_BUDGET_CHARS of the largest source files.

    Largest files are usually the most representative of the project's main
    logic; tiny files (single-line modules) are skipped.
    """
    exts = _LANGUAGE_EXTENSIONS.get(language, set())
    candidates: list[tuple[int, Path]] = []
    for ext in exts:
        for p in root.rglob(f"*{ext}"):
            if any(part in _SKIP_PARTS for part in p.parts):
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size < 64:  # skip stub-y / placeholder files
                continue
            candidates.append((size, p))

    if not candidates:
        return ""

    # Largest first — they tend to carry the architecture decisions.
    candidates.sort(reverse=True)

    out_chunks: list[str] = []
    used = 0
    for _size, p in candidates:
        try:
            text = p.read_text()
        except OSError:
            continue
        rel = p.name
        header = f"\n# === {rel} ===\n"
        remaining = _SAMPLE_BUDGET_CHARS - used - len(header)
        if remaining <= 100:
            break
        out_chunks.append(header + text[:remaining])
        used += len(header) + min(len(text), remaining)
        if used >= _SAMPLE_BUDGET_CHARS:
            break

    return "".join(out_chunks).strip()


def _parse_score(stdout: str) -> float | None:
    """Pull the first 0.x / 1.0 number out of the model output."""
    if not stdout:
        return None
    m = _SCORE_RE.search(stdout)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return max(0.0, min(1.0, v))


def _load_cache(cache_file: Path) -> float | None:
    try:
        data = json.loads(cache_file.read_text())
        v = float(data.get("score", -1))
        if 0.0 <= v <= 1.0:
            return v
    except (OSError, ValueError, TypeError):
        pass
    return None


def _write_cache(cache_file: Path, score: float, model: str) -> None:
    try:
        cache_file.write_text(json.dumps({"score": score, "model": model}))
    except OSError:
        pass
