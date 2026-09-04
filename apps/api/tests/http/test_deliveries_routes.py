from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from api.entrypoints.http.dependencies import get_delivery_history
from api.main import app


@pytest.fixture
def history():
    repository = SimpleNamespace(
        recent=AsyncMock(return_value=[]), retry=AsyncMock(return_value=True)
    )
    app.dependency_overrides[get_delivery_history] = lambda: repository

    yield repository

    app.dependency_overrides.pop(get_delivery_history, None)


def test_delivery_history_requires_authentication(client, history):
    assert client.get("/deliveries").status_code == 401
    history.recent.assert_not_awaited()


def test_delivery_history_is_bounded_and_filtered(client, owner, history):
    response = client.get("/deliveries?status=failed&limit=10")

    assert response.status_code == 200
    history.recent.assert_awaited_once_with("failed", 10)
    assert client.get("/deliveries?limit=1000000").status_code == 422


def test_failed_delivery_can_be_retried(client, owner, history):
    delivery_id = uuid4()

    assert client.post(f"/deliveries/{delivery_id}/retry").status_code == 204
    history.retry.assert_awaited_once_with(delivery_id)


def test_active_or_missing_delivery_cannot_be_retried(client, owner, history):
    history.retry.return_value = False

    assert client.post(f"/deliveries/{uuid4()}/retry").status_code == 409
