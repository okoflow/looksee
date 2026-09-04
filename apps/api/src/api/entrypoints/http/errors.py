"""Translate application failures to stable HTTP responses."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.application.errors import (
    InvalidCredentialsError,
    InvalidPayloadError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from api.domain.errors import GraphErrorCode, WorkflowGraphError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ResourceNotFoundError, _not_found)
    app.add_exception_handler(ResourceConflictError, _conflict)
    app.add_exception_handler(InvalidCredentialsError, _unauthorized)
    app.add_exception_handler(WorkflowGraphError, _invalid_graph)
    app.add_exception_handler(InvalidPayloadError, _invalid_payload)
    app.add_exception_handler(RequestValidationError, _invalid_request)


async def _invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{key: error[key] for key in ("type", "loc", "msg")} for error in exc.errors()]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errors}
    )


async def _invalid_payload(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc)},
    )


async def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


async def _conflict(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


async def _unauthorized(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
    )


async def _invalid_graph(_request: Request, exc: Exception) -> JSONResponse:
    content: dict[str, str | None] = {"detail": str(exc)}
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    if isinstance(exc, WorkflowGraphError):
        content["code"] = exc.code
        content["node_id"] = exc.node_id
        if exc.code is GraphErrorCode.FEATURE_NOT_LICENSED:
            status_code = status.HTTP_402_PAYMENT_REQUIRED

    return JSONResponse(status_code=status_code, content=content)
