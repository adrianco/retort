"""Factor registry for Design of Experiments.

Factors represent the independent variables in an experiment. Each factor has
named levels that can be categorical (unordered) or ordinal (ordered).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class FactorType(Enum):
    """Whether factor levels have a meaningful order."""

    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"


@dataclass(frozen=True)
class Factor:
    """A single experimental factor with named levels.

    Attributes:
        name: Unique identifier for this factor.
        levels: The possible values this factor can take.
        factor_type: Whether levels are categorical or ordinal.
    """

    name: str
    levels: tuple[str, ...]
    factor_type: FactorType = FactorType.CATEGORICAL

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Factor name must be non-empty")
        if len(self.levels) < 2:
            raise ValueError(
                f"Factor '{self.name}' must have at least 2 levels, got {len(self.levels)}"
            )
        if len(self.levels) != len(set(self.levels)):
            raise ValueError(f"Factor '{self.name}' has duplicate levels")

    @property
    def num_levels(self) -> int:
        return len(self.levels)

    def level_index(self, level: str) -> int:
        """Return the integer index of a level name."""
        try:
            return self.levels.index(level)
        except ValueError:
            raise ValueError(
                f"Level '{level}' not found in factor '{self.name}'. "
                f"Valid levels: {self.levels}"
            ) from None


class FactorRegistry:
    """Registry of experimental factors.

    Collects factors and provides lookups needed by the design generator.
    """

    def __init__(self) -> None:
        self._factors: dict[str, Factor] = {}

    def add(
        self,
        name: str,
        levels: Sequence[str],
        factor_type: FactorType = FactorType.CATEGORICAL,
    ) -> Factor:
        """Register a new factor.

        Args:
            name: Unique factor name.
            levels: At least 2 level names.
            factor_type: Categorical or ordinal.

        Returns:
            The created Factor.

        Raises:
            ValueError: If name is already registered or levels are invalid.
        """
        if name in self._factors:
            raise ValueError(f"Factor '{name}' is already registered")
        factor = Factor(name=name, levels=tuple(levels), factor_type=factor_type)
        self._factors[name] = factor
        return factor

    def get(self, name: str) -> Factor:
        """Retrieve a factor by name."""
        try:
            return self._factors[name]
        except KeyError:
            raise KeyError(
                f"Factor '{name}' not found. Registered: {list(self._factors)}"
            ) from None

    def remove(self, name: str) -> None:
        """Remove a factor from the registry."""
        try:
            del self._factors[name]
        except KeyError:
            raise KeyError(f"Factor '{name}' not found") from None

    @property
    def factors(self) -> list[Factor]:
        """All registered factors in insertion order."""
        return list(self._factors.values())

    @property
    def names(self) -> list[str]:
        """Names of all registered factors."""
        return list(self._factors.keys())

    def __len__(self) -> int:
        return len(self._factors)

    def __contains__(self, name: str) -> bool:
        return name in self._factors

    def level_counts(self) -> list[int]:
        """Number of levels per factor, in registration order."""
        return [f.num_levels for f in self._factors.values()]

    @classmethod
    def from_dict(cls, spec: dict[str, list[str]]) -> FactorRegistry:
        """Build a registry from a {name: [levels]} mapping.

        All factors are created as categorical. Use `add()` for ordinal factors.
        """
        registry = cls()
        for name, levels in spec.items():
            registry.add(name, levels)
        return registry
