"""High-level SIM app utilities built on top of the SIM API wrapper."""

from .ai_systems import (
    AiSystemsCollectionError,
    AiSystemsEmailCollectionResult,
    AiSystemsMcmlCollectionError,
    collect_ai_system_mcml_user_emails,
    collect_ai_system_user_emails,
)
from .mcml import McmlEmailCollectionResult, collect_mcml_master_user_emails
from .institution_heads import (
    InstitutionHead,
    InstitutionHeadsCollectionError,
    InstitutionHeadsResult,
    collect_institution_heads,
)
from .user_projects import (
    UserProjectsMembership,
    UserProjectsMembershipCollectionError,
    UserProjectsMembershipResult,
    collect_user_projects_memberships,
)

__all__ = [
    "AiSystemsCollectionError",
    "AiSystemsEmailCollectionResult",
    "AiSystemsMcmlCollectionError",
    "collect_ai_system_mcml_user_emails",
    "collect_ai_system_user_emails",
    "InstitutionHead",
    "InstitutionHeadsCollectionError",
    "InstitutionHeadsResult",
    "collect_institution_heads",
    "McmlEmailCollectionResult",
    "collect_mcml_master_user_emails",
    "UserProjectsMembership",
    "UserProjectsMembershipCollectionError",
    "UserProjectsMembershipResult",
    "collect_user_projects_memberships",
]
