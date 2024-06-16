include Makefile.dev

.PHONY: setup install-raggaeton install-raggaeton-prod install-raggaeton-dev run-raggaeton-prod run-raggaeton-dev docker-build-backend-dev docker-build-backend-prod docker-build-frontend build-and-push-all push-images
# Default values
VOLUME ?= .ragatouille/colbert/indexes

# Setup GCP credentials and project ID
setup:
	@echo "Checking for jq..."
	@if command -v jq >/dev/null 2>&1; then \
		echo "jq is already installed."; \
	else \
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

	@echo "Checking for gcloud..."
	@if command -v gcloud >/dev/null 2>&1; then \
		echo "gcloud is already installed."; \
	else \
		echo "gcloud could not be found. Do you want to install it? (y/n)"; \
		read install_gcloud; \
		if [ "$$install_gcloud" = "y" ]; then \
			echo "Downloading and installing Google Cloud SDK..."; \
			curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-367.0.0-linux-x86_64.tar.gz; \
			tar -xf google-cloud-sdk-367.0.0-linux-x86_64.tar.gz; \
			./google-cloud-sdk/install.sh -q; \
			echo "Google Cloud SDK installed."; \
			echo "Updating shell configuration for gcloud command completion..."; \
			if [ -n "$${SHELL}" ]; then \
				if [ "$${SHELL}" = "/bin/zsh" ]; then \
					echo 'source $$HOME/google-cloud-sdk/completion.zsh.inc' >> ~/.zshrc; \
					echo 'source $$HOME/google-cloud-sdk/path.zsh.inc' >> ~/.zshrc; \
				elif [ "$${SHELL}" = "/bin/bash" ]; then \
					echo 'source $$HOME/google-cloud-sdk/completion.bash.inc' >> ~/.bashrc; \
					echo 'source $$HOME/google-cloud-sdk/path.bash.inc' >> ~/.bashrc; \
				else \
					echo "Unsupported shell. Please manually add Google Cloud SDK to your shell configuration file."; \
				fi \
			else \
				echo "Shell not detected. Please manually add Google Cloud SDK to your shell configuration file."; \
			fi; \
		else \
			echo "gcloud is required to proceed. Exiting."; \
			exit 1; \
		fi \
	fi



	@echo "Please provide the path to your GCP service account credentials JSON file:"
	@read gcp_credentials_path; \
	echo "Provided GCP credentials path: $$gcp_credentials_path"; \
	if [ ! -f "$$gcp_credentials_path" ] || [ ! -s "$$gcp_credentials_path" ]; then \
		echo "Invalid file path or file is empty. Exiting."; \
		exit 1; \
	fi; \
	echo "Content of the credentials file (truncated):"; \
	sed 's/\(.\{20\}\).*/\1.../' "$$gcp_credentials_path"; \
	gcp_project_id=$$(jq -r '.project_id' "$$gcp_credentials_path"); \
	echo "Extracted GCP project ID: $$gcp_project_id"; \
	echo "GCP_CREDENTIALS_PATH=$$gcp_credentials_path" > .env; \
	echo "GCP_PROJECT_ID=$$gcp_project_id" >> .env; \
	echo "Environment variables set for backend."; \
	\
	echo "Initializing Docker Swarm..."; \
	if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q 'active'; then \
		docker swarm init; \
	else \
		echo "Docker Swarm is already active."; \
	fi; \
	\
	echo "Creating Docker secret for GCP credentials..."; \
	if docker secret ls | grep -q gcp-credentials; then \
		docker secret rm gcp-credentials; \
	fi; \
	echo "Checking file permissions and content for: $$gcp_credentials_path"; \
	echo "File path: $$gcp_credentials_path"; \
	ls -l "$$gcp_credentials_path"; \
	if [ -f "$$gcp_credentials_path" ] && [ -s "$$gcp_credentials_path" ]; then \
		echo "Creating Docker secret with file: $$gcp_credentials_path"; \
		docker secret create gcp-credentials "$$gcp_credentials_path"; \
	else \
		echo "Secret file is empty or not found."; \
		exit 1; \
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
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-backend:prod
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-frontend:latest

# Install Raggaeton by pulling development images from GCR
install-raggaeton-dev:
	@echo "Installing Raggaeton development images from GCR..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-backend:dev
	docker pull asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-frontend:latest

# Run Raggaeton for production
run-raggaeton-prod:
	@echo "Running Raggaeton for production..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker run --rm -p 8000:8000 -e ENVIRONMENT=prod asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-backend:prod &
	docker run --rm -p 3000:3000 asia.gcr.io/$(GCP_PROJECT_ID)/raggaeton-frontend:latest

# Run Raggaeton for development
run-raggaeton-dev:
	@echo "Running Raggaeton for development..."
	$(eval GCP_PROJECT_ID := $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2))
	docker-compose up --build
