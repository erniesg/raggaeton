.PHONY: setup docker-build-backend docker-build-backend-dev docker-run-backend docker-run-backend-dev docker-build-macos docker-run-macos docker-enter-backend docker-enter-backend-dev docker-build-macos-dev docker-run-macos-dev docker-enter-macos-dev

# Default values
ENVIRONMENT ?= prod
PLATFORM ?= linux/amd64
ENV_FILE ?= .env
VOLUME ?= .ragatouille/colbert/indexes

# Setup GCP credentials and project ID
setup:
	@echo "Checking for jq..."
	@if ! command -v jq &> /dev/null; then \
		echo "jq could not be found. Do you want to install it? (y/n)"; \
		read install_jq; \
		if [ "$$install_jq" = "y" ]; then \
			echo "Installing jq..."; \
			if [ "$$(uname)" = "Darwin" ]; then \
				brew install jq; \
			elif [ "$$(uname)" = "Linux" ]; then \
				sudo apt-get install -y jq; \
			else \
				echo "Unsupported OS. Please install jq manually."; \
				exit 1; \
			fi \
		else \
			echo "jq is required to proceed. Exiting."; \
			exit 1; \
		fi \
	fi
	@echo "jq is installed."
	@echo "Checking for gcloud..."
	@if ! command -v gcloud &> /dev/null; then \
		echo "gcloud could not be found. Do you want to install it? (y/n)"; \
		read install_gcloud; \
		if [ "$$install_gcloud" = "y"; then \
			curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-367.0.0-linux-x86_64.tar.gz; \
			tar -xf google-cloud-sdk-367.0.0-linux-x86_64.tar.gz; \
			./google-cloud-sdk/install.sh; \
			source ./google-cloud-sdk/path.bash.inc; \
		else \
			echo "gcloud is required to proceed. Exiting."; \
			exit 1; \
		fi \
	fi
	@echo "gcloud is installed."
	@echo "Please provide the path to your GCP service account credentials JSON file:"
	@read gcp_credentials_path; \
	gcp_project_id=$$(jq -r '.project_id' $$gcp_credentials_path); \
	echo "GCP_CREDENTIALS_PATH=$$gcp_credentials_path" > .env; \
	echo "GCP_PROJECT_ID=$$gcp_project_id" >> .env; \
	echo "Environment variables set for backend."

# Backend Docker build
docker-build-backend:
	@echo "Building Docker image for backend (${ENVIRONMENT})..."
	@if ! docker buildx inspect mybuilder &> /dev/null; then \
		echo "Creating new buildx builder instance..."; \
		docker buildx create --name mybuilder --use; \
	else \
		echo "Using existing buildx builder instance..."; \
	fi
	docker buildx inspect --bootstrap
	@echo "Running docker buildx build command..."
	docker buildx build --platform ${PLATFORM} --build-arg ENVIRONMENT=${ENVIRONMENT} -t raggaeton-tia-backend:${ENVIRONMENT} --load .

# Backend Docker build for development
docker-build-backend-dev:
	@echo "Building Docker image for backend (dev)..."
	@if ! docker buildx inspect mybuilder &> /dev/null; then \
		echo "Creating new buildx builder instance..."; \
		docker buildx create --name mybuilder --use; \
	else \
		echo "Using existing buildx builder instance..."; \
	fi
	docker buildx inspect --bootstrap
	@echo "Running docker buildx build command..."
	docker buildx build --platform ${PLATFORM} --build-arg ENVIRONMENT=dev -t raggaeton-tia-backend:dev --load .

docker-run-backend:
	@echo "Running Docker container for backend ($${ENVIRONMENT})..."
	docker run -it --rm -p 8000:8000 $$( [ -n "$${ENV_FILE}" ] && echo "--env-file $${ENV_FILE}" ) -e ENVIRONMENT=$${ENVIRONMENT} $$( [ -n "$${VOLUME}" ] && echo "-v $$(pwd)/$${VOLUME}:/app/.ragatouille/colbert/indexes" ) raggaeton-tia-backend:$${ENVIRONMENT} /bin/bash -c "\
		echo 'Contents of /app/.ragatouille/colbert/indexes:'; \
		ls -la /app/.ragatouille/colbert/indexes; \
		echo 'Checking if raggaeton/backend/src/config/ragatouille_pack exists:'; \
		ls -la /app/raggaeton/backend/src/config/ragatouille_pack || echo 'ragatouille_pack directory not found'; \
		uvicorn raggaeton.backend.src.api.endpoints.chat:app --host 0.0.0.0 --port 8000 --log-level debug"

docker-run-backend-dev:
	@echo "Running Docker container for backend (dev)..."
	docker run -it --rm -p 8000:8000 $$( [ -n "$${ENV_FILE}" ] && echo "--env-file $${ENV_FILE}" ) -e ENVIRONMENT=dev $$( [ -n "$${VOLUME}" ] && echo "-v $$(pwd)/$${VOLUME}:/app/.ragatouille/colbert/indexes" ) raggaeton-tia-backend:dev /bin/bash -c "\
		echo 'Contents of /app/.ragatouille/colbert/indexes:'; \
		ls -la /app/.ragatouille/colbert/indexes; \
		uvicorn raggaeton.backend.src.api.endpoints.chat:app --host 0.0.0.0 --port 8000 --log-level debug"
docker-run-macos:
	@echo "Running Docker containers for macOS..."
	PLATFORM=linux/arm64 make docker-run-backend ENVIRONMENT=dev ENV_FILE=$(ENV_FILE) VOLUME=$(VOLUME)

docker-run-macos-dev:
	@echo "Running Docker containers for macOS development..."
	PLATFORM=linux/arm64 make docker-run-backend-dev ENV_FILE=$(ENV_FILE) VOLUME=$(VOLUME)

# Combined Docker build and run
docker-build-and-run-backend: docker-build-backend docker-run-backend

# Combined Docker build and run for development
docker-build-and-run-backend-dev: docker-build-backend-dev docker-run-backend-dev

# Build Docker images for macOS
docker-build-macos:
	@echo "Building Docker images for macOS..."
	PLATFORM=linux/arm64 make docker-build-backend ENVIRONMENT=prod
	PLATFORM=linux/arm64 make docker-build-backend ENVIRONMENT=dev

# Build Docker images for macOS development
docker-build-macos-dev:
	@echo "Building Docker images for macOS development..."
	PLATFORM=linux/arm64 make docker-build-backend-dev

# Enter the running Docker container
docker-enter-backend:
	@echo "Entering the running Docker container for backend ($${ENVIRONMENT})..."
	@container_id=$$(docker ps -q -f "ancestor=raggaeton-tia-backend:$${ENVIRONMENT}"); \
	if [ -n "$$container_id" ]; then \
		docker exec -it $$container_id /bin/bash; \
	else \
		echo "No running container found for raggaeton-tia-backend:$${ENVIRONMENT}"; \
	fi

# Enter the running Docker container for development
docker-enter-backend-dev:
	@echo "Entering the running Docker container for backend (dev)..."
	@container_id=$$(docker ps -q -f "ancestor=raggaeton-tia-backend:dev"); \
	if [ -n "$$container_id" ]; then \
		docker exec -it $$container_id /bin/bash; \
	else \
		echo "No running container found for raggaeton-tia-backend:dev"; \
	fi

# Enter the running Docker container for macOS development
docker-enter-macos-dev:
	@echo "Entering the running Docker container for macOS development..."
	@container_id=$$(docker ps -q -f "ancestor=raggaeton-tia-backend:dev"); \
	if [ -n "$$container_id" ]; then \
		docker exec -it $$container_id /bin/bash; \
	else \
		echo "No running container found for raggaeton-tia-backend:dev"; \
	fi

# Combined Docker build and run for macOS (prod)
docker-build-and-run-backend-macos:
	PLATFORM=linux/arm64 make docker-build-backend ENVIRONMENT=prod
	PLATFORM=linux/arm64 make docker-run-backend ENVIRONMENT=prod

# Combined Docker build and run for macOS (dev)
docker-build-and-run-backend-macos-dev:
	PLATFORM=linux/arm64 make docker-build-backend-dev
	PLATFORM=linux/arm64 make docker-run-backend-dev
