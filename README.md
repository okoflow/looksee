# LookSee

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

LookSee is a self-hosted video analytics system for live streams, browser webcams, and
local video files. It runs ONNX object detection, tracks objects, derives semantic
events, and routes those events through visual workflows to alerts and external
integrations.

![Workflow editor](.github/screenshots/workflow-editor.jpg)

## Key features

- Visual workflow editor with live video, bounding boxes, events, and alerts.
- RTSP, RTMP, SRT, WHEP, browser WebRTC, and local-file inputs through MediaMTX.
- Runtime model catalog with per-workflow model, confidence, and inference-rate settings.
- Spatial, temporal, object, and conditional filters with explicit `if` and `else` branches.
- Persistent alerts, annotated snapshots, Telegram, Discord, webhook, email, and MQTT actions.
- Owner account with session auth and an encrypted credential store for integrations.
- Desired-state reconciliation that recovers camera workers after service restarts.

## Quick start

You need Docker with Compose 2.24 or later:

```bash
git clone https://github.com/okoflow/looksee.git
cd looksee
cp .env.example .env
docker compose up -d --build
```

Open the [web interface](http://127.0.0.1:3000) and create the owner account — the
defaults work out of the box. The [documentation](http://127.0.0.1:3002/docs) and the
[interactive API reference](http://127.0.0.1:8000/docs) run alongside. To run a
workflow, add a model bundle first.

> [!WARNING]
> Until the owner account is created on first launch, anyone who can reach the web
> interface can claim the instance. Run LookSee on a trusted network and do not expose
> MediaMTX or stream credentials directly to the public internet.

## Documentation

Served by the stack at [localhost:3002/docs](http://localhost:3002/docs) in English,
Russian, Hebrew, and Korean. It is still being written; until it lands, the
[release notes](https://github.com/okoflow/looksee/releases) carry what changed.

## License

Apache-2.0, except the `ee/` directory which is under the
[LookSee Enterprise license](ee/LICENSE).
