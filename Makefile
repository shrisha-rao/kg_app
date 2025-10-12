# Define Variables
IMAGE_REPO := gcr.io/kg-app-473211/research-app
TAG := v0.0.12 # latest
IMAGE_TAG := $(IMAGE_REPO):$(TAG)
DOCKERFILE := Dockerfile.cloud_dev
TF_DIR := infrastructure/dev

# --- Targets ---
.PHONY: build build-fast build-clean push deploy clean-tf

# Default target runs a cached build, push, and deployment
default: deploy

# 1. Build using cache (Fast Rebuilds)
build-fast:
	@echo "Building Docker image (fast, utilizing cache)..."
	DOCKER_BUILDKIT=1 docker build -t $(IMAGE_TAG) -f $(DOCKERFILE) .

# 2. Build ignoring cache (Forcing the fix, slow initial build)
build-clean:
	@echo "Building Docker image (clean, forcing rebuilds with --no-cache)..."
	DOCKER_BUILDKIT=1 docker build --no-cache -t $(IMAGE_TAG) -f $(DOCKERFILE) .

# 3. Push the image to the registry
push: build-fast
	@echo "Pushing image to GCR..."
	docker push $(IMAGE_TAG)

# 4. Run Terraform deployment
terraform-apply:
	@echo "Running Terraform apply..."
	cd $(TF_DIR) && terraform init
	cd $(TF_DIR) && terraform apply -auto-approve -var="image_tag=$(TAG)"

# 5. Full Deployment (Build Fast -> Push -> Terraform)
deploy: push terraform-apply
	@echo "Deployment complete."

# Utility to build and push clean image, bypassing cache.
deploy-clean: build-clean push terraform-apply
	@echo "Clean build and deployment complete."



#################################################
# Utility to destroy Terraform infrastructure
# clean-tf:
# 	@echo "Running Terraform destroy..."
# 	cd $(TF_DIR) && terraform init
# 	cd $(TF_DIR) && terraform destroy -auto-approve
