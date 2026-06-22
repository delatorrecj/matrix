# HF Docker Space — MATRIX API backend (Eclipse SUMO + FastAPI/WebSocket).
#
# HF free Spaces give you ONE container with no persistent volume and no managed Redis,
# so this image is self-contained:
#   • app code is cloned from the public repo at build time (kernel + API),
#   • the SUMO net/demand files are baked in from this Space repo (carried via Git LFS),
#   • Redis runs inside the container (start.sh; caches are ephemeral, re-seeded each boot).
# The only things you supply are the Azure OpenAI secrets (Space Settings → Secrets).
FROM python:3.12-slim

# System libs for the eclipse-sumo wheel's headless `sumo` binary:
#   • libxerces-c-dev — XML parsing; SUMO HARD-depends on it to read the .net.xml. Without
#     it the binary aborts with "error while loading shared libraries: libxerces-c..." and
#     run_nightly_baseline() fails at boot (the baseline never seeds → /simulate KeyErrors).
#   • libgdal/libproj — geo-projection used by netconvert/sumolib.
# Plus redis-server (bundled) and git+curl to clone the app at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxerces-c-dev \
    libgdal-dev \
    libproj-dev \
    libxml2 \
    redis-server \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /srv

# App code from the public repo (the SUMO net/demand are gitignored there — baked below).
# Repo root lands at /srv; the uv monorepo is /srv/app. Rebuild the Space to pull new commits.
RUN git clone --depth 1 https://github.com/delatorrecj/matrix.git . \
    && uv pip install --system --no-cache -e app/packages/kernel -e app/apps/api

# SUMO net + demand, carried in THIS Space repo (Git LFS) and baked in — no volume needed.
COPY iloilo.net.xml /srv/data/iloilo.net.xml
COPY iloilo.rou.xml /srv/data/iloilo.rou.xml

# Runtime config. Redis is local (start.sh); Chroma + HF model cache go to writable paths.
ENV MATRIX_NET_PATH=/srv/data/iloilo.net.xml \
    MATRIX_ROU_PATH=/srv/data/iloilo.rou.xml \
    MATRIX_REDIS_URL=redis://localhost:6379/0 \
    CHROMA_PATH=/srv/.chroma \
    HF_HOME=/srv/.cache/huggingface \
    MATRIX_PERSONA_LLM=0

COPY start.sh /srv/start.sh
RUN chmod +x /srv/start.sh

EXPOSE 7860
CMD ["/srv/start.sh"]
