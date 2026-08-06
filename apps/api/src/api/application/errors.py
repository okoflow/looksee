"""Application failures translated by transport entrypoints."""


class ResourceNotFoundError(LookupError):
    pass


class ResourceConflictError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass
