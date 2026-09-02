"""Edition entitlements independent of any installed ee distribution."""

from api.application.entitlements import COMMUNITY_ENTITLEMENTS, Entitlements, resolve_entitlements


def test_community_edition_allows_no_features():
    assert COMMUNITY_ENTITLEMENTS.edition == "community"
    assert COMMUNITY_ENTITLEMENTS.allows("measurement_filters") is False


def test_entitlements_allow_exactly_their_features():
    entitlements = Entitlements(edition="enterprise", features=frozenset({"a"}))

    assert entitlements.allows("a") is True
    assert entitlements.allows("b") is False


def test_missing_license_key_always_resolves_to_community():
    assert resolve_entitlements(None) is COMMUNITY_ENTITLEMENTS
