# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /raggaeton

# Install build tools including make, gcc, and python3-dev
RUN apt-get update && apt-get install -y make gcc python3-dev

# Install Poetry
RUN pip install poetry

# Copy the Poetry lock file, pyproject.toml, and Makefile first to leverage caching
COPY poetry.lock pyproject.toml Makefile /raggaeton/

# Configure Poetry to not create virtual environments
RUN poetry config virtualenvs.create false

# Install all dependencies
RUN poetry install --no-root && poetry show

# Copy the rest of the application code into the container
COPY . /raggaeton

# Ensure permissions are set correctly
RUN chown -R root:root /raggaeton

# Expose the backend port
EXPOSE 8000

# Run the application using Uvicorn
CMD ["poetry", "run", "uvicorn", "raggaeton.backend.src.api.endpoints.chat:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
