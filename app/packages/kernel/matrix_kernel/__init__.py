"""MATRIX unified simulation kernel + five glass-box impact modules.

One kernel -> one trajectory dataset -> five modules score the *same* reality
(PRD-F1). Every number carries equation_id + input_dataset_ids + a *computed*
confidence (glass-box, PRD-F14). Canonical equations: docs/methods-matrix.md.
"""
from matrix_kernel.results import Confidence, DimensionResult

__all__ = ["DimensionResult", "Confidence"]
__version__ = "0.1.0"
