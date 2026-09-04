"""MediaMTX path bodies and control-plane calls over a mocked HTTP transport."""

import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

import api.adapters.mediamtx.client as mediamtx
from api.domain.enums import CameraSource


@pytest.fixture
async def transport(monkeypatch):
    requests = []
    responder = {"handle": lambda request: httpx.Response(200, json={})}

    def handler(request):
        requests.append(request)

        return responder["handle"](request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(mediamtx, "client", client)

    yield SimpleNamespace(requests=requests, responder=responder)

    await client.aclose()


ON_DEMAND = {
    "sourceOnDemand": True,
    "sourceOnDemandStartTimeout": "10s",
    "sourceOnDemandCloseAfter": "10s",
}


@pytest.mark.parametrize(
    ("source_type", "url", "expected"),
    [
        (CameraSource.WEBRTC, "anything", {}),
        (CameraSource.RTSP, None, {}),
        (CameraSource.RTSP, "rtsp://cam/live", {"source": "rtsp://cam/live", **ON_DEMAND}),
        (CameraSource.RTMP, "rtmp://cam/live", {"source": "rtmp://cam/live", **ON_DEMAND}),
        (CameraSource.WHEP, "http://cam/whep", {"source": "whep://cam/whep", **ON_DEMAND}),
        (CameraSource.WHEP, "https://cam/whep", {"source": "wheps://cam/whep", **ON_DEMAND}),
        (CameraSource.WHEP, "whep://cam/whep", {"source": "whep://cam/whep", **ON_DEMAND}),
        (CameraSource.WHEP, "ftp://cam/whep", {}),
        (CameraSource.FILE, "../escape.mp4", {}),
    ],
)
def test_path_body_reflects_the_ingest_type(source_type, url, expected):
    assert mediamtx._path_body(source_type, url) == expected


def test_file_path_body_loops_the_cached_asset_from_the_media_mount():
    body = mediamtx._path_body(CameraSource.FILE, "0123abcd-4567ef01.mp4")

    assert body["runOnDemand"].startswith("ffmpeg ")
    assert "-i /media/0123abcd-4567ef01.mp4 " in body["runOnDemand"]
    assert body["runOnDemand"].endswith("rtsp://localhost:8554/$MTX_PATH")
    assert body["runOnDemandRestart"] is True


async def test_upsert_replaces_the_camera_path(transport):
    camera_id = uuid4()

    await mediamtx.upsert_camera_path(camera_id, CameraSource.RTSP, "rtsp://cam/live")

    [inspection, request] = transport.requests
    assert inspection.method == "GET"
    assert request.method == "POST"
    assert request.url.path == f"/v3/config/paths/replace/{camera_id}"
    assert json.loads(request.content)["source"] == "rtsp://cam/live"


async def test_upsert_surfaces_control_plane_failures(transport):
    transport.responder["handle"] = lambda request: httpx.Response(500, text="boom")

    with pytest.raises(httpx.HTTPStatusError):
        await mediamtx.upsert_camera_path(uuid4(), CameraSource.RTSP, "rtsp://cam/live")


async def test_unchanged_path_is_not_replaced_or_interrupted(transport):
    transport.responder["handle"] = lambda request: httpx.Response(
        200,
        json={"source": "rtsp://cam/live", **ON_DEMAND},
    )

    await mediamtx.upsert_camera_path(uuid4(), CameraSource.RTSP, "rtsp://cam/live")

    assert [request.method for request in transport.requests] == ["GET"]


async def test_changing_source_type_resets_previous_ingest_configuration(transport):
    transport.responder["handle"] = lambda request: httpx.Response(
        200,
        json={"source": "rtsp://old/live", **ON_DEMAND},
    )

    await mediamtx.upsert_camera_path(uuid4(), CameraSource.WEBRTC, None)

    assert [request.method for request in transport.requests] == ["GET", "POST"]
    assert json.loads(transport.requests[-1].content) == {}


async def test_failed_reconfiguration_is_retried_on_next_pass(transport):
    def fail_update(request):
        if request.method == "POST":
            return httpx.Response(503)

        return httpx.Response(200, json={"source": "rtsp://old/live", **ON_DEMAND})

    transport.responder["handle"] = fail_update
    camera_id = uuid4()

    with pytest.raises(httpx.HTTPStatusError):
        await mediamtx.upsert_camera_path(camera_id, CameraSource.RTSP, "rtsp://new/live")

    transport.responder["handle"] = lambda request: httpx.Response(200, json={})
    await mediamtx.upsert_camera_path(camera_id, CameraSource.RTSP, "rtsp://new/live")

    assert [request.method for request in transport.requests] == ["GET", "POST", "GET", "POST"]


async def test_list_walks_every_page(transport):
    pages = [
        {"pageCount": 2, "items": [{"name": "a"}, {"name": "b"}]},
        {"pageCount": 2, "items": [{"name": "c"}]},
    ]
    transport.responder["handle"] = lambda request: httpx.Response(
        200, json=pages[int(request.url.params["page"])]
    )

    names = await mediamtx.list_path_names()

    assert names == {"a", "b", "c"}
    assert [r.url.params["page"] for r in transport.requests] == ["0", "1"]
    assert transport.requests[0].url.params["itemsPerPage"] == "1000"


async def test_list_stops_at_an_empty_page(transport):
    transport.responder["handle"] = lambda request: httpx.Response(
        200, json={"pageCount": 5, "items": []}
    )

    assert await mediamtx.list_path_names() == set()
    assert len(transport.requests) == 1


async def test_list_raises_on_transport_errors(transport):
    transport.responder["handle"] = lambda request: httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        await mediamtx.list_path_names()


@pytest.mark.parametrize("status_code", [200, 404])
async def test_delete_treats_missing_paths_as_success(transport, status_code, caplog):
    transport.responder["handle"] = lambda request: httpx.Response(status_code)
    camera_id = uuid4()

    await mediamtx.delete_camera_path(camera_id)

    assert transport.requests[0].method == "DELETE"
    assert transport.requests[0].url.path == f"/v3/config/paths/delete/{camera_id}"
    assert caplog.text == ""


async def test_delete_logs_but_swallows_failures(transport, caplog):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    transport.responder["handle"] = refuse
    camera_id = uuid4()

    await mediamtx.delete_camera_path(camera_id)

    assert f"mediamtx delete failed camera={camera_id}" in caplog.text
