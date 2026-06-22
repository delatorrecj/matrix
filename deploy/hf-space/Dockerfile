FROM python:3.12-slim

# System libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libproj-dev \
    libxml2 \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Install uv (no global pip pollution)
RUN pip install --no-cache-dir uv

# Copy the app to the working directory, as the "user" user
COPY --chown=user ../../app/packages/kernel/pyproject.toml ./packages/kernel/pyproject.toml
COPY --chown=user ../../app/apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY --chown=user ../../app/packages/kernel ./packages/kernel
COPY --chown=user ../../app/apps/api ./apps/api

# Install kernel + API
RUN uv pip install --system --no-cache -e packages/kernel -e apps/api

ENV MATRIX_NET_PATH=/data/iloilo.net.xml \
    MATRIX_ROU_PATH=/data/iloilo.rou.xml

EXPOSE 7860

CMD ["uvicorn", "matrix_api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
