import httpx

from api.application.errors import DeliveryError


def http_delivery_error(error: httpx.HTTPError) -> DeliveryError:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code

        return DeliveryError(f"HTTP {status}", retryable=status in (408, 429) or status >= 500)

    return DeliveryError("HTTP transport unavailable")
