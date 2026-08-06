"""Inference use cases independent of FastStream and Redis."""

from inference.application.pool import WorkerPool
from inference.application.worker import CameraWorker, WorkerDependencies

__all__ = ["CameraWorker", "WorkerDependencies", "WorkerPool"]
