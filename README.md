# LookSee

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

LookSee is a self-hosted video analytics system for live streams, browser webcams, and
local video files. It runs ONNX object detection, tracks objects, derives semantic
events, and routes those events through visual workflows to alerts and external
integrations.

![Workflow editor](.github/screenshots/workflow-editor.jpg)

## Quick start

You need Docker with Compose 2.24 or later:

```bash
git clone https://github.com/okoflow/looksee.git
cd looksee
cp .env.example .env
docker compose up -d --build
```

Open the [web interface](http://127.0.0.1:3000) and create the owner account — the
defaults work out of the box.

> [!WARNING]
> Until the owner account is created on first launch, anyone who can reach the web
> interface can claim the instance. Run LookSee on a trusted network and do not expose
> MediaMTX or stream credentials directly to the public internet.

## License

Apache-2.0, except the `ee/` directory which is under the
[LookSee Enterprise license](ee/LICENSE).
