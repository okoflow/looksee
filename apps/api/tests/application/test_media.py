from uuid import uuid4

import pytest

from api.adapters.security.media import JwtMediaTokens
from api.application.errors import InvalidCredentialsError, ResourceNotFoundError
from api.application.media import MediaAccess, MediaGrant
from api.domain.enums import CameraSource


@pytest.fixture
def media():
    class Repository:
        def __init__(self):
            self.cameras = {}
            self.users = set()

        async def camera_source(self, camera_id):
            return self.cameras.get(camera_id)

        async def user_exists(self, user_id):
            return user_id in self.users

    repository = Repository()
    user_id, camera_id = uuid4(), uuid4()
    repository.cameras[camera_id] = CameraSource.WEBRTC
    repository.users.add(user_id)
    tokens = JwtMediaTokens()
    access = MediaAccess(repository, tokens, service_user="media", service_password="private")

    return access, repository, tokens, user_id, camera_id


async def authorize(access, camera_id, **overrides):
    fields = {
        "action": "read",
        "path": str(camera_id),
        "token": "",
        "user": "",
        "password": "",
        "ip": "203.0.113.1",
        "protocol": "webrtc",
    }
    fields.update(overrides)

    return await access.authorize(**fields)


@pytest.mark.parametrize("action", ["read", "publish"])
async def test_camera_grant_authorizes_only_its_action(media, action):
    access, _repository, _tokens, user_id, camera_id = media
    token = await access.issue(user_id, camera_id, action)

    assert await authorize(access, camera_id, action=action, token=token)
    assert not await authorize(
        access, camera_id, action="publish" if action == "read" else "read", token=token
    )


async def test_grant_cannot_be_reused_for_another_camera(media):
    access, repository, _tokens, user_id, camera_id = media
    other_camera = uuid4()
    repository.cameras[other_camera] = CameraSource.WEBRTC
    token = await access.issue(user_id, camera_id, "read")

    assert not await authorize(access, other_camera, token=token)


async def test_deleting_user_revokes_existing_media_grants(media):
    access, repository, _tokens, user_id, camera_id = media
    token = await access.issue(user_id, camera_id, "read")
    repository.users.remove(user_id)

    assert not await authorize(access, camera_id, token=token)


@pytest.mark.parametrize("path", ["all_others", "../camera", "not-a-uuid", ""])
async def test_arbitrary_paths_are_denied_even_to_service_user(media, path):
    access, _repository, _tokens, _user_id, camera_id = media

    assert not await authorize(access, camera_id, path=path, user="media", password="private")


async def test_control_api_requires_private_service_credentials(media):
    access, _repository, _tokens, user_id, camera_id = media
    token = await access.issue(user_id, camera_id, "read")

    assert await authorize(access, camera_id, action="api", user="media", password="private")
    assert not await authorize(access, camera_id, action="api", token=token)
    assert not await authorize(access, camera_id, action="api", user="media", password="wrong")


@pytest.mark.parametrize("source", [CameraSource.RTSP, CameraSource.FILE])
async def test_browser_cannot_replace_managed_camera_sources(media, source):
    access, repository, tokens, user_id, camera_id = media
    repository.cameras[camera_id] = source

    with pytest.raises(InvalidCredentialsError):
        await access.issue(user_id, camera_id, "publish")

    token = tokens.issue(MediaGrant(user_id, camera_id, "publish"))

    assert not await authorize(access, camera_id, action="publish", token=token)


@pytest.mark.parametrize(
    ("ip", "protocol", "allowed"),
    [
        ("127.0.0.1", "rtsp", True),
        ("::1", "rtsp", True),
        ("203.0.113.1", "rtsp", False),
        ("127.0.0.1", "webrtc", False),
        ("bad", "rtsp", False),
    ],
)
async def test_file_publisher_requires_mediamtx_loopback(media, ip, protocol, allowed):
    access, repository, _tokens, _user_id, camera_id = media
    repository.cameras[camera_id] = CameraSource.FILE

    assert await authorize(access, camera_id, action="publish", ip=ip, protocol=protocol) is allowed


async def test_missing_camera_cannot_receive_grant(media):
    access, _repository, _tokens, user_id, _camera_id = media

    with pytest.raises(ResourceNotFoundError):
        await access.issue(user_id, uuid4(), "read")
