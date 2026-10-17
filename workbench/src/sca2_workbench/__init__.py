"""SCA2 workbench — tensor hooks and (later slices) the adapter-brain views.

Slice 1 ships ``sca2_workbench.hooks`` only; see ``workbench/spec/conservation.md``.
"""

from .hooks import (
    EPS_QUADRANT_III,
    clamp_quadrant_iii,
    dla_abs_gap,
    residual_inf_norm,
    swiglu_poles,
)

__all__ = [
    "EPS_QUADRANT_III",
    "clamp_quadrant_iii",
    "dla_abs_gap",
    "residual_inf_norm",
    "swiglu_poles",
]
