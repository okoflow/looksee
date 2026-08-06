"""Entitlement resolution for the enterprise edition.

A present license key currently unlocks every feature; offline signed
license files (Ed25519 over plan, features, and expiry) replace this
check once license issuing ships.
"""

from api.application.entitlements import COMMUNITY_ENTITLEMENTS, Entitlements
from ee.features import ALL_FEATURES


def resolve_entitlements(license_key: str | None) -> Entitlements:
    if license_key is None:
        return COMMUNITY_ENTITLEMENTS

    return Entitlements(edition="enterprise", features=ALL_FEATURES)
