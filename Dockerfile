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

# Install dependencies using Poetry
RUN echo "Installing dependencies..." \
    && if [ "$ENVIRONMENT" = "prod" ]; then \
        poetry install --no-dev --no-root; \
    else \
        poetry install --no-root; \
    fi \
    && poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && $VENV_PATH/bin/pip install -r requirements.txt \
    && rm -rf /root/.local

# Verify installed packages
RUN echo "Installed packages:" \
    && $VENV_PATH/bin/pip list

# Copy the rest of the application code
COPY . .

# Install the application package
RUN echo "Installing application package..." \
    && . $VENV_PATH/bin/activate && pip install -e .

# Verify Git installation
RUN git --version

# Production stage
FROM python-base as production
ARG ENVIRONMENT=prod
RUN apt-get update && apt-get install --no-install-recommends -y build-essential git && git --version
COPY --from=builder $VENV_PATH $VENV_PATH
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="$VENV_PATH/bin:$PATH"
EXPOSE 8000

# Use Docker secret for .env file
RUN --mount=type=secret,id=env,dst=/run/secrets/.env \
    echo "Checking for .env file..." \
    && if [ -f /run/secrets/.env ]; then \
        echo ".env file found and loaded"; \
        export $(cat /run/secrets/.env | xargs); \
    else \
        echo ".env file not found, relying on environment variables"; \
    fi

# Ensure the virtual environment is activated
CMD ["/bin/bash", "-c", ". /opt/venv/bin/activate && uvicorn raggaeton.backend.src.api.endpoints.chat:app --host 0.0.0.0 --port 8000 --log-level info"]

# Development stage
FROM python-base as development
ARG ENVIRONMENT=dev
RUN apt-get update && apt-get install --no-install-recommends -y build-essential git && git --version
COPY --from=builder $VENV_PATH $VENV_PATH
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="$VENV_PATH/bin:$PATH"
EXPOSE 8000

# Use Docker secret for .env file
RUN --mount=type=secret,id=env,dst=/run/secrets/.env \
    echo "Checking for .env file..." \
    && if [ -f /run/secrets/.env ]; then \
        echo ".env file found and loaded"; \
        export $(cat /run/secrets/.env | xargs); \
    else \
        echo ".env file not found, relying on environment variables"; \
    fi

# Ensure the virtual environment is activated
CMD ["/bin/bash", "-c", ". /opt/venv/bin/activate && uvicorn raggaeton.backend.src.api.endpoints.chat:app --host 0.0.0.0 --port 8000 --log-level debug"]
