"""Confounding/aliasing inspector for fractional factorial designs.

In a fractional factorial design, certain effects are aliased (confounded)
with one another — they cannot be estimated independently. The aliasing
structure depends on the design resolution:

- Resolution III: main effects are aliased with two-factor interactions.
- Resolution IV: two-factor interactions are aliased with each other,
  but main effects are clear of two-factor interactions.
- Resolution V+: main effects and two-factor interactions are estimable;
  aliasing occurs among higher-order interactions only.

This module computes the aliasing structure by analysing the generator
columns of a fractional factorial design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from retort.design.factors import FactorRegistry
from retort.design.generator import DesignPhase


@dataclass(frozen=True)
class AliasGroup:
    """A group of effects that are aliased (confounded) with one another.

    Attributes:
        effects: Tuple of effect labels in this alias group.
            Main effects are single factor names (e.g. "A").
            Interactions are joined with ":" (e.g. "A:B").
    """

    effects: tuple[str, ...]

    @property
    def order(self) -> int:
        """Order of the lowest-order effect in the group."""
        return min(len(e.split(":")) for e in self.effects)

    @property
    def is_clear(self) -> bool:
        """True if this group contains only one effect (no aliasing)."""
        return len(self.effects) == 1


@dataclass
class AliasingReport:
    """Complete aliasing structure for a fractional factorial design.

    Attributes:
        factor_names: Factor names in the design, labelled A, B, C, ...
        factor_labels: Mapping from letter label to factor name.
        resolution: Design resolution (III=3, IV=4, etc.).
        n_runs: Number of runs in the design.
        n_factors: Number of factors.
        alias_groups: List of alias groups.
        generators: Generator words used to construct the design.
        defining_relation: The defining relation (set of words that equal I).
    """

    factor_names: list[str]
    factor_labels: dict[str, str]
    resolution: int
    n_runs: int
    n_factors: int
    alias_groups: list[AliasGroup] = field(default_factory=list)
    generators: list[str] = field(default_factory=list)
    defining_relation: list[str] = field(default_factory=list)

    @property
    def clear_main_effects(self) -> list[str]:
        """Main effects that are not aliased with other main effects."""
        clear = []
        for group in self.alias_groups:
            main_in_group = [e for e in group.effects if ":" not in e]
            if len(main_in_group) == 1 and group.is_clear:
                clear.append(main_in_group[0])
            elif len(main_in_group) == 1:
                # aliased but only one main effect — still estimable
                clear.append(main_in_group[0])
        return clear

    @property
    def confounded_pairs(self) -> list[tuple[str, str]]:
        """Pairs of effects that are confounded with each other."""
        pairs = []
        for group in self.alias_groups:
            if not group.is_clear:
                for a, b in combinations(group.effects, 2):
                    pairs.append((a, b))
        return pairs


def _letters(n: int) -> list[str]:
    """Generate uppercase letter labels for n factors."""
    return [chr(ord("A") + i) for i in range(n)]


def _word_product(w1: str, w2: str) -> str:
    """Multiply two defining words (XOR of factor sets).

    In the algebra of defining relations, multiplying two words is the
    symmetric difference of their factor sets (factors appearing in both
    cancel out).
    """
    letters1 = set(w1)
    letters2 = set(w2)
    result = sorted(letters1.symmetric_difference(letters2))
    return "".join(result) if result else "I"


def _all_defining_words(generators: list[str], labels: list[str]) -> list[str]:
    """Compute the full defining relation from the generator words.

    Each generator is a word like "ABC" meaning the generated column equals
    the product of columns A, B, C. The generator word itself is obtained by
    multiplying by the identity of the generated column.

    The full defining relation includes:
    - All individual generator words
    - All products of pairs, triples, etc. of generator words
    """
    n_base = len(labels) - len(generators)

    # Each generator column is labelled with the next letter after base columns
    # The defining word for generator i is: generated_letter * generator_product
    defining_words = []
    for i, gen in enumerate(generators):
        gen_letter = labels[n_base + i]
        word = _word_product(gen_letter, gen)
        defining_words.append(word)

    # Build full defining relation by taking all subset products
    full_relation = list(defining_words)
    n = len(defining_words)
    for size in range(2, n + 1):
        for combo in combinations(range(n), size):
            product = defining_words[combo[0]]
            for idx in combo[1:]:
                product = _word_product(product, defining_words[idx])
            if product != "I" and product not in full_relation:
                full_relation.append(product)

    return sorted(full_relation, key=lambda w: (len(w), w))


def _compute_aliases(
    effect: str,
    defining_relation: list[str],
) -> list[str]:
    """Compute the alias chain for a given effect.

    The alias of effect X with defining word W is X*W.
    """
    aliases = []
    for word in defining_relation:
        alias = _word_product(effect, word)
        if alias != effect and alias != "I":
            aliases.append(alias)
    return aliases


def _effect_label(letters_in_effect: str, factor_labels: dict[str, str]) -> str:
    """Convert a letter-based effect to a named-factor label.

    E.g. "AB" with labels {A: "language", B: "agent"} → "language:agent"
    """
    parts = [factor_labels.get(ch, ch) for ch in letters_in_effect]
    return ":".join(parts)


def compute_aliasing(
    registry: FactorRegistry,
    phase: DesignPhase | str,
    *,
    max_order: int = 3,
) -> AliasingReport:
    """Compute the aliasing structure for a fractional factorial design.

    Analyses the generator columns to determine which effects are aliased
    (confounded) with one another.

    Args:
        registry: Factor registry defining the factors and levels.
        phase: Design phase (determines resolution).
        max_order: Maximum interaction order to include in the analysis.
            1 = main effects only, 2 = up to two-factor interactions, etc.

    Returns:
        AliasingReport with the complete aliasing structure.
    """
    if isinstance(phase, str):
        phase = DesignPhase(phase)

    factors = registry.factors
    n_factors = len(factors)

    if n_factors < 2:
        raise ValueError("Need at least 2 factors for aliasing analysis")

    resolution = 3 if phase == DesignPhase.SCREENING else 4
    labels = _letters(n_factors)
    factor_labels = {label: f.name for label, f in zip(labels, factors)}

    # Determine the base/generated split
    from retort.design.generator import (
        _interaction_generators,
        _min_base_factors,
    )

    n_base = _min_base_factors(n_factors, resolution)
    n_base = min(n_base, n_factors)
    n_generated = n_factors - n_base

    if n_generated == 0:
        # Full factorial — no aliasing
        n_runs = 2**n_factors
        all_effects: list[str] = []
        for order in range(1, min(max_order, n_factors) + 1):
            for combo in combinations(labels, order):
                all_effects.append("".join(combo))

        alias_groups = [
            AliasGroup(effects=(_effect_label(e, factor_labels),))
            for e in all_effects
        ]
        return AliasingReport(
            factor_names=[f.name for f in factors],
            factor_labels=factor_labels,
            resolution=min(n_factors + 1, 99),
            n_runs=n_runs,
            n_factors=n_factors,
            alias_groups=alias_groups,
            generators=[],
            defining_relation=[],
        )

    # Get the generators used by the design generator
    base_letters = [chr(ord("a") + i) for i in range(n_base)]
    gen_products = _interaction_generators(base_letters, n_generated)
    # Convert to uppercase for our algebra
    generators_upper = [g.upper() for g in gen_products]

    n_runs = 2**n_base

    # Compute defining relation
    defining_relation = _all_defining_words(generators_upper, labels)

    # Compute actual resolution from defining relation
    actual_resolution = min(len(w) for w in defining_relation) if defining_relation else n_factors + 1

    # Enumerate all effects up to max_order
    all_effects = []
    for order in range(1, min(max_order, n_factors) + 1):
        for combo in combinations(labels, order):
            all_effects.append("".join(combo))

    # Build alias groups
    visited: set[str] = set()
    alias_groups: list[AliasGroup] = []

    for effect in all_effects:
        if effect in visited:
            continue
        aliases = _compute_aliases(effect, defining_relation)
        # Filter to only effects within our max_order
        relevant_aliases = [
            a for a in aliases if len(a) <= max_order and a in all_effects
        ]
        group_effects = [effect] + relevant_aliases
        # Convert to named labels
        named = tuple(_effect_label(e, factor_labels) for e in group_effects)
        alias_groups.append(AliasGroup(effects=named))
        visited.add(effect)
        for a in relevant_aliases:
            visited.add(a)

    return AliasingReport(
        factor_names=[f.name for f in factors],
        factor_labels=factor_labels,
        resolution=actual_resolution,
        n_runs=n_runs,
        n_factors=n_factors,
        alias_groups=alias_groups,
        generators=generators_upper,
        defining_relation=defining_relation,
    )
