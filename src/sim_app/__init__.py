"""High-level SIM app utilities built on top of the SIM API wrapper."""

from .ai_systems import (
    AiSystemsCollectionError,
    AiSystemsEmailCollectionResult,
    AiSystemsMcmlCollectionError,
    collect_ai_system_mcml_user_emails,
    collect_ai_system_user_emails,
)
from .mcml import McmlEmailCollectionResult, collect_mcml_master_user_emails

__all__ = [
    "AiSystemsCollectionError",
    "AiSystemsEmailCollectionResult",
    "AiSystemsMcmlCollectionError",
    "collect_ai_system_mcml_user_emails",
    "collect_ai_system_user_emails",
    "McmlEmailCollectionResult",
    "collect_mcml_master_user_emails",
]
