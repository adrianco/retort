"""Design of Experiments generation for retort."""

from retort.design.augmentor import AugmentationResult, augment_design
from retort.design.factors import Factor, FactorRegistry
from retort.design.generator import DesignMatrix, DesignPhase, generate_design

__all__ = [
    "AugmentationResult",
    "DesignMatrix",
    "DesignPhase",
    "Factor",
    "FactorRegistry",
    "augment_design",
    "generate_design",
]
