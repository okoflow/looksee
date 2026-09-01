ARG NODE_IMAGE=node:24-slim
ARG PNPM_VERSION=11.11.0

FROM ${NODE_IMAGE} AS base

ARG PNPM_VERSION

ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH NEXT_TELEMETRY_DISABLED=1

RUN npm install --global pnpm@${PNPM_VERSION}

WORKDIR /repo/apps/studio

FROM base AS deps

COPY apps/studio/package.json apps/studio/pnpm-lock.yaml apps/studio/pnpm-workspace.yaml ./

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile --ignore-scripts

FROM base AS builder

ENV NODE_ENV=production

COPY --from=deps /repo/apps/studio/node_modules ./node_modules
COPY apps/studio/ ./

RUN pnpm build

FROM ${NODE_IMAGE} AS runner

ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000

WORKDIR /app

COPY --from=builder --chown=node:node /repo/apps/studio/.next/standalone ./
COPY --from=builder --chown=node:node /repo/apps/studio/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
