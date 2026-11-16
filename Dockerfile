# syntax=docker/dockerfile:1
# jithendar.com's app image: moks-cms built for this site, on the moks-cms-builder image that moks-cms's CI pushes
# (registry.jithendar.com/jithendar/moks-cms-builder:<tag>; the tag this site runs is "builder" in moks-cms.json).
# A copy of moks-cms's services/www/Dockerfile.site. The build context is this repository; Dockerfile.dockerignore
# keeps it to site.json, config/, content/ and public/images/.
#
#   docker build --platform linux/arm64 \
#     --build-arg MOKS_CMS_BUILDER=registry.jithendar.com/jithendar/moks-cms-builder:"$(jq -r .builder moks-cms.json)" \
#     --build-arg GIT_SHA="$(git rev-parse HEAD)" -t jithendar-com:dev .
#
# Built, smoke-tested, pushed and rolled out by .github/workflows/release.yml (job `app`).
ARG MOKS_CMS_BUILDER=registry.jithendar.com/jithendar/moks-cms-builder:latest
FROM ${MOKS_CMS_BUILDER} AS build
COPY . /site
# APP_ENV is baked into the meta robots tag at build time; production is the only indexable value.
ARG APP_ENV=production
ENV APP_ENV=$APP_ENV SITE_DIR=/site
# The builder keeps the test fixture site (tests/fixtures/site) for its own checks. Output tracing would copy its
# public/images into the standalone output (the image lookups are dynamic), so it goes before the build.
RUN rm -rf tests/fixtures/site && npm run site -- --copy && npm run build

FROM node:26-bookworm-slim
WORKDIR /app
# GIT_SHA is reported by /api/health so CI can confirm which build is live (the site's commit); MOKS_CMS_REVISION is
# the moks-cms commit its builder was made from.
ARG GIT_SHA=dev
ARG MOKS_CMS_REVISION=unknown
ENV NODE_ENV=production APP_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000 GIT_SHA=$GIT_SHA \
  MOKS_CMS_REVISION=$MOKS_CMS_REVISION
COPY --from=build --chown=1000:1000 /moks-cms/services/www/.next/standalone ./
COPY --from=build --chown=1000:1000 /moks-cms/services/www/.next/static ./.next/static
COPY --from=build --chown=1000:1000 /moks-cms/services/www/public ./public
USER 1000:1000
EXPOSE 3000
CMD ["node", "server.js"]
