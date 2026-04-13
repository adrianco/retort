"""Pydantic models for workspace.yaml configuration.

Covers all top-level sections: factors, responses, tasks, playpen, design, promotion.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Experiment metadata (visibility, naming)
# ---------------------------------------------------------------------------

Visibility = Literal["public", "private"]


class ExperimentConfig(BaseModel):
    """Experiment-level metadata.

    ``visibility`` controls which artifacts may be published outside the
    workspace. It defaults to ``"private"`` (fail-closed) so that omitting
    the field — or copy-pasting a public example for confidential work —
    never accidentally leaks proprietary code, task specs, or reports.
    """

    name: Annotated[str | None, Field(default=None, description="Human-readable experiment name")]
    visibility: Annotated[Visibility, Field(default="private", description="public = artifacts safe to publish; private = local-only")]


# ---------------------------------------------------------------------------
# Factors
# ---------------------------------------------------------------------------

class Factor(BaseModel):
    """A single experimental factor with categorical levels."""

    levels: Annotated[list[str], Field(min_length=1, description="Categorical levels for this factor")]

    @model_validator(mode="after")
    def levels_unique(self) -> Factor:
        if len(self.levels) != len(set(self.levels)):
            raise ValueError("factor levels must be unique")
        return self


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class ResponseMetric(BaseModel):
    """A named response metric.  When the YAML value is a plain string the
    name is set and defaults apply; when it is a mapping the extra fields
    override defaults."""

    name: str
    weight: Annotated[float, Field(default=1.0, gt=0, description="Relative weight in multi-objective ranking")]
    direction: Annotated[str, Field(default="maximize", pattern="^(maximize|minimize)$")]


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskSource(BaseModel):
    """A task source specification.

    Supported URI schemes: ``bundled://``, ``git://``, ``local://``.
    """

    source: Annotated[str, Field(description="Task source URI (bundled://, git://, local://)")]

    @model_validator(mode="after")
    def valid_scheme(self) -> TaskSource:
        valid = ("bundled://", "git://", "local://")
        if not any(self.source.startswith(s) for s in valid):
            raise ValueError(f"task source must start with one of {valid}, got {self.source!r}")
        return self


# ---------------------------------------------------------------------------
# Playpen
# ---------------------------------------------------------------------------

class RunnerType(str, Enum):
    docker = "docker"
    cloud = "cloud"
    local = "local"


class PlaypenConfig(BaseModel):
    """Configuration for experiment execution environment."""

    runner: Annotated[RunnerType, Field(default=RunnerType.docker)]
    replicates: Annotated[int, Field(default=3, ge=1, description="Runs per design point")]
    timeout_minutes: Annotated[int, Field(default=30, ge=1)]
    cost_limit_usd: Annotated[float | None, Field(default=None, ge=0, description="Spend cap per screening phase")]


# ---------------------------------------------------------------------------
# Design
# ---------------------------------------------------------------------------

class DesignConfig(BaseModel):
    """Statistical design parameters."""

    screening_resolution: Annotated[int, Field(default=3, ge=2, le=6)]
    characterization_resolution: Annotated[int, Field(default=4, ge=3, le=6)]
    significance_threshold: Annotated[float, Field(default=0.10, gt=0, lt=1)]


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------

class PromotionGate(BaseModel, extra="allow"):
    """A single promotion gate with configurable thresholds.

    Known fields are validated; unknown fields are preserved so organisations
    can extend gate definitions without forking the schema.
    """

    p_value: Annotated[float | None, Field(default=None, gt=0, lt=1)]
    posterior_confidence: Annotated[float | None, Field(default=None, gt=0, le=1)]
    dominated_confidence: Annotated[float | None, Field(default=None, gt=0, le=1)]


class PromotionConfig(BaseModel):
    """Promotion gate configuration for lifecycle transitions."""

    screening_to_trial: Annotated[PromotionGate, Field(default_factory=lambda: PromotionGate(p_value=0.10))]
    trial_to_production: Annotated[PromotionGate, Field(default_factory=lambda: PromotionGate(posterior_confidence=0.80))]
    production_to_retired: Annotated[PromotionGate, Field(default_factory=lambda: PromotionGate(dominated_confidence=0.95))]


# ---------------------------------------------------------------------------
# Top-level workspace
# ---------------------------------------------------------------------------

def _parse_responses(raw: list[str | dict[str, Any]]) -> list[ResponseMetric]:
    """Normalise a mixed list of strings / dicts into ResponseMetric objects."""
    out: list[ResponseMetric] = []
    for item in raw:
        if isinstance(item, str):
            out.append(ResponseMetric(name=item))
        elif isinstance(item, dict):
            out.append(ResponseMetric(**item))
        else:
            raise ValueError(f"response entry must be a string or mapping, got {type(item)}")
    return out


class WorkspaceConfig(BaseModel):
    """Root configuration model for a Retort workspace.yaml file."""

    experiment: Annotated[ExperimentConfig, Field(default_factory=ExperimentConfig)]
    factors: Annotated[dict[str, Factor], Field(min_length=1, description="Experimental factors")]
    responses: Annotated[list[ResponseMetric], Field(min_length=1, description="Response metrics to measure")]
    tasks: Annotated[list[TaskSource], Field(min_length=1, description="Task source specifications")]
    playpen: Annotated[PlaypenConfig, Field(default_factory=PlaypenConfig)]
    design: Annotated[DesignConfig, Field(default_factory=DesignConfig)]
    promotion: Annotated[PromotionConfig, Field(default_factory=PromotionConfig)]

    @model_validator(mode="before")
    @classmethod
    def coerce_responses(cls, data: Any) -> Any:
        """Allow responses to be plain strings or rich mappings."""
        if isinstance(data, dict) and "responses" in data:
            data["responses"] = _parse_responses(data["responses"])
        return data
