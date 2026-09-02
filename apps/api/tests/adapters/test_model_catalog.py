"""Model bundle discovery from a directory of manifests."""

import json

import pytest

from api.adapters.filesystem.model_catalog import ModelCatalog, event_kind_for_label


def write_bundle(models_dir, model_id, manifest, weights=b"onnx"):
    bundle = models_dir / model_id
    bundle.mkdir(parents=True)
    (bundle / "model.onnx").write_bytes(weights)
    (bundle / "manifest.json").write_text(json.dumps(manifest))

    return bundle


@pytest.fixture
def models_dir(tmp_path):
    return tmp_path / "models"


@pytest.fixture
def catalog(models_dir):
    return ModelCatalog(models_dir)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("person", "PERSON_DETECTED"),
        ("trafficLight-Red", "TRAFFICLIGHT_RED_DETECTED"),
        ("space empty", "SPACE_EMPTY_DETECTED"),
        ("123", "CLASS_123_DETECTED"),
        ("already_DETECTED", "ALREADY_DETECTED"),
        ("!!!", None),
    ],
)
def test_labels_normalize_into_event_kinds(label, expected):
    assert event_kind_for_label(label) == expected


def test_bundle_loads_with_derived_and_overridden_events(models_dir, catalog):
    write_bundle(
        models_dir,
        "fire",
        {
            "name": "Fire & smoke",
            "labels": ["fire", "other", "smoke"],
            "recommended_confidence_threshold": 0.3,
            "events": {"other": None, "smoke": "SMOKE_SEEN"},
        },
    )

    model = catalog.get("fire")

    assert model.name == "Fire & smoke"
    assert model.recommended_confidence_threshold == 0.3
    assert [(c.class_id, c.label, c.event_kind) for c in model.classes] == [
        (0, "fire", "FIRE_DETECTED"),
        (1, "other", None),
        (2, "smoke", "SMOKE_SEEN"),
    ]


def test_missing_name_falls_back_to_a_title_from_the_id(models_dir, catalog):
    write_bundle(models_dir, "dfine-m_ppe", {"labels": ["helmet"]})

    assert catalog.get("dfine-m_ppe").name == "Dfine M Ppe"


@pytest.mark.parametrize("model_id", ["ghost", "Bad Id", "../fire", ""])
def test_unknown_or_malformed_ids_yield_nothing(models_dir, catalog, model_id):
    write_bundle(models_dir, "fire", {"labels": ["fire"]})

    assert catalog.get(model_id) is None


def test_bundle_without_manifest_is_skipped_with_a_warning(models_dir, catalog, caplog):
    bundle = write_bundle(models_dir, "fire", {"labels": ["fire"]})
    (bundle / "manifest.json").unlink()

    assert catalog.get("fire") is None
    assert "missing manifest.json" in caplog.text


def test_invalid_manifest_is_skipped_with_a_warning(models_dir, catalog, caplog):
    write_bundle(models_dir, "fire", {"labels": ["fire", "fire"]})

    assert catalog.get("fire") is None
    assert "invalid model asset" in caplog.text


def test_list_discovers_bundles_in_id_order(models_dir, catalog):
    write_bundle(models_dir, "zebra", {"labels": ["zebra"]})
    write_bundle(models_dir, "apple", {"labels": ["apple"]})
    (models_dir / "notabundle").mkdir()

    assert [model.id for model in catalog.list()] == ["apple", "zebra"]


def test_list_of_a_missing_directory_is_empty(catalog):
    assert catalog.list() == ()


def test_changed_bundle_keeps_the_cached_model_and_warns_once(models_dir, catalog, caplog):
    bundle = write_bundle(models_dir, "fire", {"name": "Before", "labels": ["fire"]})
    catalog.get("fire")
    (bundle / "manifest.json").write_text(
        json.dumps({"name": "After!", "labels": ["fire", "smoke"]})
    )

    first = catalog.list()
    second = catalog.list()

    assert first[0].name == "Before"
    assert second[0].name == "Before"
    assert caplog.text.count("model asset changed after discovery") == 1
