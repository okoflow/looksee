import shared


def test_every_exported_name_resolves():
    unresolved = [name for name in shared.__all__ if not hasattr(shared, name)]

    assert unresolved == []


def test_public_surface_is_the_documented_contract():
    assert set(shared.__all__) == {
        "MANIFEST_FILENAME",
        "MODEL_FILENAME",
        "Channel",
        "Detection",
        "DetectionFrame",
        "EventKind",
        "ModelId",
        "StartStream",
        "StopStream",
        "StreamCommand",
        "WorkerErrored",
        "WorkerEvent",
        "WorkerStarted",
        "WorkerStopped",
        "WorkflowConfig",
        "bundle_model_path",
        "camera_id_from_path_name",
        "camera_path_name",
        "last_frame_key",
        "read_manifest",
    }
