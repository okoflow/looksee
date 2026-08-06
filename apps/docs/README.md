# Documentation site

LookSee's documentation, built with [Fumadocs](https://fumadocs.dev) on Next.js. The
compose stack serves it at `http://localhost:3002/docs`.

Content lives in [`content/docs/`](content/docs) as MDX; navigation order is defined in
`content/docs/meta.json`.

## Run locally

```bash
pnpm -C apps/docs install --frozen-lockfile
pnpm -C apps/docs dev
```
