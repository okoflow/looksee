# Inference service

The inference service turns camera frames into tracked detections. It receives desired
camera runs from Valkey, reads normalized RTSP paths from MediaMTX, loads ONNX models, and
publishes strict detection and worker-lifecycle messages. It does not know workflow
filters, event policy, alerts, or notification actions.

## Layout

```text
src/inference/
├── application/     camera worker, worker pool, and adapter protocols
├── adapters/onnx/   detector cache, signature registry, and model adapters
├── adapters/video/  MediaMTX URL construction and background RTSP decoding
├── adapters/redis/  detection, lifecycle, and last-frame output
├── adapters/        JPEG encoding and ByteTrack integration
├── entrypoints/     FastStream application and command subscriber
├── config.py
└── main.py
```

## Run locally

Complete the root [development setup](../../README.md#develop-locally), including the CPU
extra and native `.env` URLs, then:

```bash
uv run --package looksee-inference faststream run inference.main:app
```

## Add an ONNX architecture

Model selection is based on tensor signatures, never model IDs. Add an
`OnnxDetectionAdapter` implementation under `src/inference/adapters/onnx/models/` with a
strict `supports(signature)` predicate, return `supervision.Detections` from
`detect(frame)`, and register the adapter type in `src/inference/adapters/onnx/registry.py`.

See the [shared package](../../packages/shared/README.md) before changing command or event
payloads.
