FROM python:3.12-slim
# tzdata so TZ resolves to a real zone - session times are shown local
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
# Stamped by the GitHub workflow; local builds show dev/unknown.
ARG APP_VERSION=dev
ARG GIT_COMMIT=unknown
ENV APP_VERSION=$APP_VERSION GIT_COMMIT=$GIT_COMMIT
# Not root: the arena needs nothing but its own database. Existing data
# directories from older images belong to root - chown them to 1000 once.
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin arena \
    && mkdir -p /data && chown arena:arena /data
USER arena
VOLUME /data
EXPOSE 8090
# /api/health reads the database, so a broken volume shows up as unhealthy
# instead of as a blank page nobody notices.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request as u, sys; \
sys.exit(0 if u.urlopen('http://127.0.0.1:8090/api/health', timeout=4).status == 200 else 1)"
# The caller's address is resolved by the app itself (auth.peer_address):
# CF-Connecting-IP or the last X-Forwarded-For entry, and only from peers in
# ARENA_TRUSTED_PROXIES (default: loopback and private networks, where
# cloudflared or a reverse proxy sits). uvicorn's own --proxy-headers takes
# the *first* X-Forwarded-For entry, which the client writes.
# --ws-max-size: a full backfill (20,000 samples) is about 2.5 MiB.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--ws-max-size", "4194304"]
