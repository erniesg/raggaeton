include Makefile.dev

.PHONY: setup install-raggaeton install-raggaeton-prod install-raggaeton-dev run-raggaeton-prod run-raggaeton-dev docker-build-backend-dev docker-build-backend-prod docker-build-frontend build-and-push-all push-images
# Default values
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
	@echo "Initializing Docker Swarm..."
	@if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q 'active'; then \
		docker swarm init; \
	else \
		echo "Docker Swarm is already active."; \
	fi
	@echo "Creating Docker secret for GCP credentials..."
	@if ! docker secret ls | grep -q gcp-credentials; then \
		docker secret create gcp-credentials $$gcp_credentials_path; \
	else \
		echo "Docker secret 'gcp-credentials' already exists."; \
	fi

# Install Raggaeton by pulling images from GCR (both prod and dev)
install-raggaeton:
	@echo "Installing Raggaeton by pulling images from GCR..."
	make install-raggaeton-prod
	make install-raggaeton-dev

# Install Raggaeton by pulling production images from GCR
install-raggaeton-prod:
	@echo "Installing Raggaeton production images from GCR..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-backend:prod
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-frontend:latest

# Install Raggaeton by pulling development images from GCR
install-raggaeton-dev:
	@echo "Installing Raggaeton development images from GCR..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-backend:dev
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-frontend:latest

# Run Raggaeton for production
run-raggaeton-prod:
	@echo "Running Raggaeton for production..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker run --rm -p 8000:8000 -e ENVIRONMENT=prod asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-backend:prod &
	docker run --rm -p 3000:3000 asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-tia-frontend:latest

# Run Raggaeton for development
run-raggaeton-dev:
	@echo "Running Raggaeton for development..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker-compose up --build
