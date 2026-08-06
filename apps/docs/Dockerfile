ARG NODE_IMAGE=node:24-slim
ARG PNPM_VERSION=11.11.0

FROM ${NODE_IMAGE} AS base

ARG PNPM_VERSION

ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH NEXT_TELEMETRY_DISABLED=1

RUN npm install --global pnpm@${PNPM_VERSION}

WORKDIR /repo/apps/docs

FROM base AS deps

COPY packages/brand /repo/packages/brand
COPY apps/docs/package.json apps/docs/pnpm-lock.yaml apps/docs/pnpm-workspace.yaml ./

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile --ignore-scripts

FROM base AS builder

ENV NODE_ENV=production

COPY --from=deps /repo/packages/brand /repo/packages/brand
COPY --from=deps /repo/apps/docs/node_modules ./node_modules
COPY apps/docs/ ./

RUN pnpm build

FROM ${NODE_IMAGE} AS runner

ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000

WORKDIR /app

COPY --from=builder --chown=node:node /repo/apps/docs/.next/standalone ./
COPY --from=builder --chown=node:node /repo/apps/docs/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
