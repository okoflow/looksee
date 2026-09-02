import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from shared import MANIFEST_FILENAME, MODEL_FILENAME, EventKind, bundle_model_path, read_manifest
from shared.model_assets import ModelManifest

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATHS = sorted(REPO_ROOT.glob("models/*/manifest.json"))
EVENT_KIND = TypeAdapter(EventKind)


def test_bundle_layout_constants():
    assert MODEL_FILENAME == "model.onnx"
    assert MANIFEST_FILENAME == "manifest.json"


def test_bundle_model_path_nests_weights_under_model_id(tmp_path):
    assert bundle_model_path(tmp_path, "dfine-m-ppe") == tmp_path / "dfine-m-ppe" / "model.onnx"


def test_read_manifest_parses_file_beside_weights(tmp_path):
    bundle_dir = tmp_path / "dfine-m-ppe"
    bundle_dir.mkdir()
    (bundle_dir / MANIFEST_FILENAME).write_text(json.dumps({"labels": ["head", "helmet"]}))

    manifest = read_manifest(bundle_dir)

    assert manifest.labels == {0: "head", 1: "helmet"}


def test_read_manifest_fails_when_file_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_manifest(tmp_path)


def test_label_list_positions_become_class_ids():
    manifest = ModelManifest(labels=["fire", "other", "smoke"])

    assert manifest.labels == {0: "fire", 1: "other", 2: "smoke"}


def test_label_map_keys_are_parsed_and_sorted_by_class_id():
    manifest = ModelManifest.model_validate_json(
        '{"labels": {"2": "smoke", "0": "fire", "1": "other"}}'
    )

    assert list(manifest.labels.items()) == [(0, "fire"), (1, "other"), (2, "smoke")]


def test_defaults_leave_optional_metadata_empty():
    manifest = ModelManifest(labels=["fire"])

    assert manifest.name is None
    assert manifest.recommended_confidence_threshold is None
    assert manifest.events == {}


def test_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelManifest(labels=["fire"], version=2)


def test_requires_labels():
    with pytest.raises(ValidationError, match=r"labels\s+Field required"):
        ModelManifest()


def test_rejects_empty_label_list():
    with pytest.raises(ValidationError, match="at least one class label is required"):
        ModelManifest(labels=[])


@pytest.mark.parametrize("labels", [{0: "fire", 2: "smoke"}, {1: "fire", 2: "smoke"}])
def test_rejects_non_contiguous_class_ids(labels):
    with pytest.raises(ValidationError, match="contiguous and start at zero"):
        ModelManifest(labels=labels)


def test_rejects_negative_class_ids():
    with pytest.raises(ValidationError, match="greater_than_equal"):
        ModelManifest(labels={-1: "fire", 0: "smoke"})


def test_rejects_duplicate_labels():
    with pytest.raises(ValidationError, match="class labels must be unique"):
        ModelManifest(labels=["fire", "fire"])


def test_strips_whitespace_around_labels():
    manifest = ModelManifest(labels=["  fire ", "smoke"])

    assert manifest.labels == {0: "fire", 1: "smoke"}


def test_rejects_blank_labels():
    with pytest.raises(ValidationError, match="string_too_short"):
        ModelManifest(labels=["   "])


def test_events_may_silence_a_label_with_none():
    manifest = ModelManifest(labels=["fire", "other"], events={"other": None})

    assert manifest.events == {"other": None}


def test_events_must_reference_known_labels():
    with pytest.raises(ValidationError, match="events map unknown labels: flame, spark"):
        ModelManifest(labels=["fire"], events={"spark": "SPARK", "flame": None})


@pytest.mark.parametrize("kind", ["FIRE", "FIRE_DETECTED", "A1_B2"])
def test_event_kind_accepts_upper_snake_case(kind):
    assert EVENT_KIND.validate_python(kind) == kind


@pytest.mark.parametrize("kind", ["", "fire", "Fire", "1FIRE", "FIRE-DETECTED", "_FIRE", "F" * 65])
def test_event_kind_rejects_other_shapes(kind):
    with pytest.raises(ValidationError):
        EVENT_KIND.validate_python(kind)


@pytest.mark.parametrize("threshold", [-0.01, 1.01])
def test_rejects_threshold_outside_unit_range(threshold):
    with pytest.raises(ValidationError, match="recommended_confidence_threshold"):
        ModelManifest(labels=["fire"], recommended_confidence_threshold=threshold)


@pytest.mark.parametrize("name", ["", "n" * 129])
def test_rejects_name_outside_length_bounds(name):
    with pytest.raises(ValidationError, match="name"):
        ModelManifest(labels=["fire"], name=name)


def test_round_trips_through_json():
    manifest = ModelManifest(
        name="Fire & smoke",
        labels=["fire", "smoke"],
        recommended_confidence_threshold=0.3,
        events={"fire": "FIRE_DETECTED"},
    )

    restored = ModelManifest.model_validate_json(manifest.model_dump_json())

    assert restored == manifest


@pytest.mark.skipif(not MANIFEST_PATHS, reason="no model bundles under models/")
@pytest.mark.parametrize("manifest_path", MANIFEST_PATHS, ids=lambda path: path.parent.name)
def test_bundled_manifest_parses(manifest_path):
    manifest = read_manifest(manifest_path.parent)

    assert manifest.labels
