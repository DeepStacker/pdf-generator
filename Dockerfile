# Web build of the Audit Engine, for the home server.
#
# Installed editable on purpose. The package ships data files the server reads
# from disk at runtime — the built SPA under audit_engine_web/static, the
# desktop template under audit_engine/ui/static, plus fonts, settings and
# templates. A plain `pip install .` copies only the Python modules, so those
# would be missing and the app would serve a blank page. Editable keeps the
# source tree as the install, exactly as the previous host ran it.

# ---------------------------------------------------------------------------
# The browser front end, built from source.
#
# Its output used to be committed and copied in from the host, so a change to
# web/src only reached production if someone also remembered to run the build
# and commit the bundle. Building it here means the image can only ever
# contain what the source says, and a clean clone deploys correctly.
#
# web/src/index.css imports the desktop's tokens.css and web.css by relative
# path -- one palette, both front ends -- so those have to be present here in
# the same shape the repo has them, not just the web/ directory.
# ---------------------------------------------------------------------------
FROM node:22-slim AS webbuild
WORKDIR /build
COPY web/package.json web/package-lock.json ./web/
RUN cd web && npm ci --no-audit --no-fund
COPY src/audit_engine/ui/static/tokens.css src/audit_engine/ui/static/web.css ./src/audit_engine/ui/static/
COPY web/ ./web/
RUN cd web && npm run build


FROM python:3.12-slim

# Faster, quieter, and no .pyc litter in the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so a code change does not reinstall pandas every build.
COPY pyproject.toml README.md* ./
COPY src/audit_engine/_version.py src/audit_engine/_version.py
RUN python - <<'PY' > /tmp/reqs.txt
import tomllib
with open("pyproject.toml", "rb") as fh:
    print("\n".join(tomllib.load(fh)["project"]["dependencies"]))
PY
RUN pip install -r /tmp/reqs.txt

COPY . .

# The front end from the stage above. Comes after COPY . . so it cannot be
# shadowed by anything that slipped through .dockerignore.
COPY --from=webbuild /build/audit_engine_web/static/ audit_engine_web/static/

RUN pip install --no-deps -e .

# Runs unprivileged. /data is the only writable path it needs; everything the
# app keeps — the SQLite history and the report storage — is pinned there by
# environment variables so nothing lands in a layer that a rebuild discards.
RUN useradd --create-home --uid 10001 audit \
    && mkdir -p /data/reports \
    && chown -R audit:audit /data /app
USER audit

ENV PORT=8080 \
    REPORT_STORAGE_DIR=/data/reports \
    AUDIT_ENGINE_DB_PATH=/data/audit_engine.db \
    AUDIT_ENGINE_LOG_PATH=/data/audit_engine.log

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/', timeout=4).status==200 else 1)"

CMD ["audit-engine-web", "--host", "0.0.0.0", "--port", "8080"]
