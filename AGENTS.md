# LookSee

Self-hosted video analytics system for live streams, browser webcams, and local
video files. It runs ONNX object detection, tracks objects, derives semantic
events, and routes those events through visual workflows to alerts and external
integrations.

Monorepo: `apps/api` (FastAPI control plane), `apps/inference` (ONNX detection
service), `apps/studio` (Next.js workflow editor), `packages/shared`
(api ↔ inference wire contracts), `ee/` (commercial edition code under
`ee/LICENSE`, everything else is Apache-2.0). Documentation lives in the
[looksee-docs](https://github.com/okoflow/looksee-docs) repository.
