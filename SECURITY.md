# Security policy

This page covers which versions of Looksee are supported, how to report a vulnerability, and what is in scope. Looksee is self-hosted software that ingests video, stores credentials for external integrations, and exposes a web interface.

## Supported versions

| Version                       | Supported                        |
| ----------------------------- | -------------------------------- |
| The latest release and `main` | Yes                              |
| Older releases                | No, update to the latest release |

## Reporting a vulnerability

Report a vulnerability through [GitHub private vulnerability reporting](https://github.com/okoflow/looksee/security/advisories/new). Don't open a public issue, pull request, or discussion for a security problem.

Include what helps reproduce and assess the issue:

- The affected component (`api`, `inference`, `studio`, `shared`, `ee`, compose, or Docker images) and the commit or release version.
- Steps to reproduce, a proof of concept, or the request that triggers it.
- The impact you expect, and the deployment shape it applies to (Docker Compose, native, behind a reverse proxy).

You receive an acknowledgment within three business days and a triage decision within seven business days. A confirmed vulnerability is fixed in a patch release and disclosed in a GitHub security advisory that credits you, unless you ask otherwise. Keep the report private until the advisory is published.

## Scope

In scope: everything in this repository, including the API, the inference service, Studio, the shared contracts, the Enterprise code under `ee/`, `compose.yaml`, the Dockerfiles, and the published container images.

Out of scope: vulnerabilities in upstream projects such as MediaMTX, PostgreSQL, Valkey, or ONNX Runtime unless a Looksee default configuration causes them; deployments that ignore the hardening notes below; denial of service by saturating a camera stream you are entitled to publish.

## Hardening a deployment

- Create the owner account immediately after the first start. Until it exists, anyone who can reach the web interface can claim the instance.
- Set private `POSTGRES_PASSWORD`, `MTX_MEDIA_PASSWORD`, and `STORAGE_PASSWORD` values. They are backend secrets: browsers receive short-lived, camera-scoped grants from the API instead of the MediaMTX password.
- Put Studio and the API behind a reverse proxy with TLS, set `AUTH_COOKIE_SECURE=true`, and narrow `CORS_ORIGIN_REGEX` to your origin.
- Set `SECRET_KEY` explicitly or back up the `api_keys` volume. It signs sessions and encrypts stored credentials; losing it invalidates both.
- PostgreSQL, Valkey, the video storage, and the MediaMTX control API bind to `127.0.0.1`. RTSP (`8554`) and WebRTC (`8889`, `8189/udp`) bind to all interfaces so cameras and browsers can reach them; firewall them to the networks that need access.
- Keep the stack on a trusted network. Do not expose MediaMTX, camera credentials, or the database to the public internet.

## Dependencies

Dependabot watches the uv workspace, the Studio package set, the Docker base images, `compose.yaml`, and GitHub Actions. Lock files (`uv.lock`, `pnpm-lock.yaml`) are committed, and images pin their base tags.
