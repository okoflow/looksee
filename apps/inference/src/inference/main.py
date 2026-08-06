"""Compatibility module for the deployed ``inference.main:app`` entrypoint."""

from inference.entrypoints.faststream import app

__all__ = ["app"]
