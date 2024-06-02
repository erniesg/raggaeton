.PHONY: setup docker-pull docker-build-backend docker-build-frontend docker-run-backend docker-run-frontend docker-build docker-run docker-tag docker-push docker-deploy

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
		if [ "$$install_gcloud" = "y" ]; then \
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

# Pull Docker images
docker-pull:
	@echo "Pulling Docker images..."
	docker pull raggaeton-tia-backend:latest
	docker pull raggaeton-tia-frontend:latest

# Backend Docker build for multiple platforms
docker-build-backend:
	@echo "Building Docker image for backend..."
	docker buildx create --name mybuilder --use || true
	docker buildx inspect --bootstrap
	docker buildx build --no-cache --platform linux/amd64,linux/arm64 -t raggaeton-tia-backend:latest --progress=plain .

# Frontend Docker build
docker-build-frontend:
	@echo "Building Docker image for frontend..."
	cd /Users/erniesg/code/erniesg/raggaeton-frontend && docker build --no-cache -t raggaeton-tia-frontend -f Dockerfile .

# Combined Docker build
docker-build: docker-build-backend docker-build-frontend

# Backend Docker run
docker-run-backend:
	@echo "Running Docker container for backend..."
	docker run --env-file .env -v $(shell pwd):/raggaeton -p 8000:8000 raggaeton-tia-backend:latest

# Frontend Docker run
docker-run-frontend:
	@echo "Running Docker container for frontend..."
	docker run -p 3000:3000 raggaeton-tia-frontend

# Combined Docker run using Docker Compose
docker-run:
	@echo "Starting services with Docker Compose..."
	docker-compose up --build

# Tag Docker images for GCR
docker-tag:
	@echo "Tagging Docker images for GCR..."
	docker tag raggaeton-tia-backend:latest gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-backend:latest
	docker tag raggaeton-tia-frontend:latest gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-frontend:latest

# Push Docker images to GCR
docker-push:
	@echo "Pushing Docker images to GCR..."
	docker push gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-backend:latest
	docker push gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-frontend:latest

# Combined tag and push
docker-deploy: docker-tag docker-push
