"""SQLAlchemy models for experiment runs, results, factor levels, and design matrices."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class LifecyclePhase(str, enum.Enum):
    candidate = "candidate"
    screening = "screening"
    trial = "trial"
    production = "production"
    retired = "retired"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FactorLevel(Base):
    """A factor (e.g. 'language') and one of its categorical levels (e.g. 'python')."""

    __tablename__ = "factor_levels"

    id = Column(Integer, primary_key=True)
    factor_name = Column(String(128), nullable=False, index=True)
    level_name = Column(String(128), nullable=False)
    ordinal = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("factor_name", "level_name", name="uq_factor_level"),
    )

    def __repr__(self) -> str:
        return f"<FactorLevel {self.factor_name}={self.level_name}>"


class DesignMatrix(Base):
    """A design matrix for a specific experimental phase."""

    __tablename__ = "design_matrices"

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    phase = Column(Enum(LifecyclePhase), nullable=False, default=LifecyclePhase.screening)
    resolution = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    description = Column(Text, nullable=True)

    rows = relationship("DesignMatrixRow", back_populates="matrix", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DesignMatrix {self.name!r} phase={self.phase.value}>"


class DesignMatrixRow(Base):
    """A single row (treatment combination) in a design matrix."""

    __tablename__ = "design_matrix_rows"

    id = Column(Integer, primary_key=True)
    matrix_id = Column(Integer, ForeignKey("design_matrices.id"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)

    matrix = relationship("DesignMatrix", back_populates="rows")
    cells = relationship("DesignMatrixCell", back_populates="row", cascade="all, delete-orphan")
    runs = relationship("ExperimentRun", back_populates="design_row")

    __table_args__ = (
        UniqueConstraint("matrix_id", "row_index", name="uq_matrix_row"),
    )

    def __repr__(self) -> str:
        return f"<DesignMatrixRow matrix={self.matrix_id} row={self.row_index}>"


class DesignMatrixCell(Base):
    """A single cell — maps a design-matrix row to a factor level."""

    __tablename__ = "design_matrix_cells"

    id = Column(Integer, primary_key=True)
    row_id = Column(Integer, ForeignKey("design_matrix_rows.id"), nullable=False, index=True)
    factor_level_id = Column(Integer, ForeignKey("factor_levels.id"), nullable=False)

    row = relationship("DesignMatrixRow", back_populates="cells")
    factor_level = relationship("FactorLevel")

    __table_args__ = (
        UniqueConstraint("row_id", "factor_level_id", name="uq_row_factor"),
    )


class ExperimentRun(Base):
    """A single execution of an experiment for one design-matrix row."""

    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True)
    design_row_id = Column(Integer, ForeignKey("design_matrix_rows.id"), nullable=False, index=True)
    replicate = Column(Integer, nullable=False, default=1)
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.pending)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    design_row = relationship("DesignMatrixRow", back_populates="runs")
    results = relationship("RunResult", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("design_row_id", "replicate", name="uq_run_replicate"),
    )

    def __repr__(self) -> str:
        return f"<ExperimentRun id={self.id} status={self.status.value}>"


class RunResult(Base):
    """A scored response metric for one experiment run."""

    __tablename__ = "run_results"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=False, index=True)
    metric_name = Column(String(128), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(64), nullable=True)
    metadata_json = Column(Text, nullable=True)

    run = relationship("ExperimentRun", back_populates="results")

    __table_args__ = (
        UniqueConstraint("run_id", "metric_name", name="uq_run_metric"),
    )

    def __repr__(self) -> str:
        return f"<RunResult run={self.run_id} {self.metric_name}={self.value}>"
