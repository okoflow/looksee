"""Application failures translated by transport entrypoints."""


class ResourceNotFoundError(LookupError):
    pass


class ResourceConflictError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class InvalidPayloadError(ValueError):
    """Invalid user input, without the potentially secret submitted values."""


class DeliveryError(Exception):
    def __init__(self, reason: str, *, retryable: bool = True) -> None:
        super().__init__(reason)
        self.retryable = retryable


class RetryableFrameError(Exception):
    pass


class AssetStoreUnavailableError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Video storage is unavailable. Check its connection and S3 credentials.")
