"""Edition entitlements: which licensed features this deployment may run.

This module and api.domain.workflow.extensions are the only two places the
open codebase may import ee.
"""

from dataclasses import dataclass
from typing import Literal

Edition = Literal["community", "enterprise"]


@dataclass(frozen=True, slots=True)
class Entitlements:
    edition: Edition
    features: frozenset[str]

    def allows(self, feature: str) -> bool:
        return feature in self.features


COMMUNITY_ENTITLEMENTS = Entitlements(edition="community", features=frozenset())


def resolve_entitlements(license_key: str | None) -> Entitlements:
    """Community unless the installed ee distribution grants more."""
    try:
        from ee.license import resolve_entitlements as resolve_ee_entitlements
    except ImportError:
        return COMMUNITY_ENTITLEMENTS

    return resolve_ee_entitlements(license_key)
