"""Entitlements and model catalog read endpoints."""


def test_entitlements_default_to_community(client, owner):
    response = client.get("/entitlements")

    assert response.status_code == 200
    assert response.json() == {"edition": "community", "features": []}


def test_entitlements_list_licensed_features_sorted(client, owner, grant_enterprise):
    grant_enterprise()

    assert client.get("/entitlements").json() == {
        "edition": "enterprise",
        "features": ["enterprise_integrations", "measurement_filters"],
    }


def test_models_come_from_the_catalog(client, owner):
    response = client.get("/models")

    [model] = response.json()
    assert response.status_code == 200
    assert model["id"] == "people"
    assert model["recommended_confidence_threshold"] == 0.4
    assert [c["event_kind"] for c in model["classes"]] == ["PERSON_DETECTED", "CAR_DETECTED", None]
