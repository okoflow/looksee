# Studio

Studio is LookSee's Next.js interface for creating workflows and observing
them in real time. It provides a graph editor, model-aware node configuration, live WHEP
playback, browser-webcam publishing, detection overlays, event feeds, and alert history.

## Layout

```text
src/
├── app/       Next.js route groups: (auth) sign-in/setup, (studio) guarded shell
├── _app/      application providers and global styles
├── _pages/    workflow, credentials, sign-in, and setup page compositions
├── widgets/   sidebar, canvas, inspector, palette, and live dock
├── features/  camera publishing/playback, workflow interactions, credential management
├── entities/  workflow, inference-model, alert, credential, and session domain slices
└── shared/    API client, runtime configuration, routes, utilities, and UI primitives
```

The application follows Feature-Sliced Design. Import across slices through each slice's
public `index.ts`, use relative imports inside a slice, and keep dependencies directed
downward from pages and widgets toward features, entities, and shared code.

## Run locally

```bash
pnpm -C apps/studio install --frozen-lockfile
pnpm -C apps/studio dev
```

The interface is served at `http://localhost:3000` and expects the API and MediaMTX on
their default localhost ports.

## Runtime configuration

The server validates public runtime values on each request and injects them into the page,
so a deployed image can be repointed without rebuilding: `RUNTIME_API_URL`,
`RUNTIME_WS_URL`, `RUNTIME_MEDIAMTX_WEBRTC_URL`, `RUNTIME_MEDIAMTX_MEDIA_USER`,
`RUNTIME_MEDIAMTX_MEDIA_PASSWORD`, `RUNTIME_DOCS_URL`, `RUNTIME_GITHUB_URL`. These values,
including the MediaMTX credentials, are visible to the browser — treat them as access
details for a trusted deployment, not as private backend secrets.

`SERVER_API_URL` is server-only: the auth guard resolves sessions against it, so inside
compose it points at the internal `http://api:8000` service address.
