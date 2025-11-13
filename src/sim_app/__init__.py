"""High-level SIM app utilities built on top of the SIM API wrapper."""

from .mcml import McmlEmailCollectionResult, collect_mcml_master_user_emails

__all__ = [
    "McmlEmailCollectionResult",
    "collect_mcml_master_user_emails",
]
