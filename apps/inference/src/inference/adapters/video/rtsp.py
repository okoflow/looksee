from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from typing import TYPE_CHECKING

import av
import janus

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

_INITIAL_RETRY_DELAY = 0.5
_MAX_RETRY_DELAY = 30.0
_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 10.0
_STOP_TIMEOUT = _READ_TIMEOUT + 2.0
_FALLBACK_SOURCE_FPS = 25.0
_FRAME_QUEUE_SIZE = 2
_LOW_LATENCY_OPTIONS = {
    "fflags": "nobuffer",
    "flags": "low_delay",
    "reorder_queue_size": "0",
    "probesize": "32",
    "analyzeduration": "0",
}


def _source_fps(stream: av.VideoStream) -> float:
    """Declared stream rate, falling back when the container reports none or nonsense."""
    average_rate = stream.average_rate
    if average_rate is None or average_rate <= 0:
        return _FALLBACK_SOURCE_FPS

    return float(average_rate)


class RtspReader:
    """Background-thread RTSP decoder feeding an async frame queue."""

    def __init__(
        self,
        rtsp_url: str,
        target_fps: int,
        transport: str,
        source_name: str,
    ) -> None:
        self._frames: janus.Queue[np.ndarray] = janus.Queue(maxsize=_FRAME_QUEUE_SIZE)
        self._rtsp_url = rtsp_url
        self._target_fps = target_fps
        self._transport = transport
        self._source_name = source_name
        self._stop_requested = threading.Event()
        self._last_frame_at = 0.0
        self._started = False
        self._thread = threading.Thread(
            target=self._decode_with_retries,
            name=f"rtsp:{source_name}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()
        self._started = True

    def set_target_fps(self, target_fps: int) -> None:
        self._target_fps = target_fps

    async def next_frame(self) -> np.ndarray:
        frame = await self._frames.async_q.get()
        self._frames.async_q.task_done()

        return frame

    async def stop(self) -> None:
        try:
            await asyncio.to_thread(self._stop_and_join)
        finally:
            await self._frames.aclose()

    def _stop_and_join(self) -> None:
        self._stop_requested.set()

        if not self._started:
            return

        self._thread.join(timeout=_STOP_TIMEOUT)
        if self._thread.is_alive():
            logger.warning("rtsp decoder did not stop source=%s", self._source_name)

    def _decode_with_retries(self) -> None:
        retry_delay = _INITIAL_RETRY_DELAY
        while not self._stop_requested.is_set():
            attempt_started_at = time.monotonic()
            try:
                self._decode_until_closed()
                retry_delay = _INITIAL_RETRY_DELAY
            except Exception as exc:
                if self._stop_requested.is_set():
                    return

                if self._last_frame_at >= attempt_started_at:
                    retry_delay = _INITIAL_RETRY_DELAY

                level = logging.WARNING if isinstance(exc, av.FFmpegError) else logging.ERROR
                logger.log(
                    level,
                    "rtsp decode failed source=%s retry=%.1fs",
                    self._source_name,
                    retry_delay,
                )

            if self._stop_requested.wait(timeout=retry_delay):
                return

            retry_delay = min(retry_delay * 2.0, _MAX_RETRY_DELAY)

    def _decode_until_closed(self) -> None:
        options = {"rtsp_transport": self._transport, **_LOW_LATENCY_OPTIONS}
        # (open, read) timeouts interrupt blocked ffmpeg io from inside the decode
        # thread; closing the container from another thread is not safe.
        container = av.open(
            self._rtsp_url, options=options, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT)
        )

        try:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"

            source_fps = _source_fps(stream)
            frame_index = 0

            for packet in container.demux(stream):
                if self._stop_requested.is_set():
                    return

                if packet.dts is None:
                    continue

                for frame in packet.decode():
                    keep_every_nth = max(1, round(source_fps / self._target_fps))
                    if frame_index % keep_every_nth == 0:
                        bgr_frame = frame.to_ndarray(format="bgr24")
                        self._enqueue_frame(bgr_frame)
                        self._last_frame_at = time.monotonic()
                    frame_index += 1
        finally:
            container.close()

    def _enqueue_frame(self, frame: np.ndarray) -> None:
        while not self._stop_requested.is_set():
            try:
                self._frames.sync_q.put_nowait(frame)
                return
            except queue.Full:
                try:
                    self._frames.sync_q.get_nowait()
                except queue.Empty:
                    continue
                self._frames.sync_q.task_done()
