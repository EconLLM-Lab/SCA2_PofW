"""sca2_validity: minimal validity-profile engine for SCA2 (no cvprofiles dependency)."""

from sca2_validity.engine import (
    Beta,
    Network,
    Restriction,
    Roles,
    run_identify,
    run_theta_grid,
    slack_matrix,
)
from sca2_validity.freeze import PACKAGE_VERSION as __version__

__all__ = [
    "Beta",
    "Network",
    "Restriction",
    "Roles",
    "run_identify",
    "run_theta_grid",
    "slack_matrix",
    "__version__",
]
