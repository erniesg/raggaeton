# Base image
FROM python:3.10-slim as python-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH="/opt/venv" \
    PATH="$VENV_PATH/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH"

# Builder stage
FROM python-base as builder
ARG ENVIRONMENT=prod
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential libpq-dev gettext curl git \
    && python3 -m venv $VENV_PATH \
    && $VENV_PATH/bin/pip install --upgrade pip

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy pyproject.toml and poetry.lock
WORKDIR /app
COPY pyproject.toml poetry.lock ./

RUN echo "Installing dependencies..." \
&& if [ "$ENVIRONMENT" = "prod" ]; then \
    poetry install --no-dev --no-root; \
else \
    poetry install --no-root; \
fi \
&& poetry export -f requirements.txt --output requirements.txt --without-hashes \
&& echo "Requirements:" \
&& cat requirements.txt \
&& $VENV_PATH/bin/pip install -r requirements.txt \
&& rm -rf /root/.local

# Verify installed packages
RUN echo "Installed packages:" \
    && $VENV_PATH/bin/pip list

# Copy the rest of the application code
COPY . .

# Copy the .ragatouille directory
COPY .ragatouille /app/.ragatouille

# Install the application package
RUN echo "Installing application package..." \
    && . $VENV_PATH/bin/activate && pip install -e .

# Verify Git installation
RUN git --version

# Final stage
FROM python-base as final
ARG ENVIRONMENT=prod
RUN apt-get update && apt-get install --no-install-recommends -y build-essential git && git --version
COPY --from=builder $VENV_PATH $VENV_PATH
WORKDIR /app
COPY --from=builder /app /app

RUN --mount=type=secret,id=env,dst=/run/secrets/.env \
if grep -q GCP_CREDENTIALS_PATH /run/secrets/.env; then \
    export GCP_CREDENTIALS_PATH=$(grep GCP_CREDENTIALS_PATH /run/secrets/.env | cut -d '=' -f2); \
    echo "GCP_CREDENTIALS_PATH found in .env, using mounted credentials file at $GCP_CREDENTIALS_PATH"; \
    export GOOGLE_APPLICATION_CREDENTIALS=$GCP_CREDENTIALS_PATH; \
else \
    echo "GCP_CREDENTIALS_PATH not found in .env, skipping credentials file"; \
fi
ENV PATH="$VENV_PATH/bin:$PATH"
EXPOSE 8000

# Use Docker secret for .env file
RUN --mount=type=secret,id=env,dst=/run/secrets/.env \
    echo "Checking for .env file..." \
    && if [ -f /run/secrets/.env ]; then \
        echo ".env file found and loaded"; \
        cp /run/secrets/.env /app/.env; \
    else \
        echo ".env file not found, relying on environment variables"; \
    fi

# Set the log level based on the environment
ARG LOG_LEVEL=info
ENV LOG_LEVEL=${LOG_LEVEL}

# Ensure the virtual environment is activated
CMD /bin/bash -c "\
    if [ -f /app/gcp-credentials.json ]; then export GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json; fi && \
    . /opt/venv/bin/activate && \
    if [ -f /app/.env ]; then export \$(grep -v '^#' /app/.env | xargs); fi && \
    if [ \"$$ENVIRONMENT\" = \"dev\" ]; then export LOG_LEVEL=debug; else export LOG_LEVEL=info; fi && \
    uvicorn raggaeton.backend.src.api.endpoints.chat:app --host 0.0.0.0 --port 8000 --log-level \$$LOG_LEVEL"
