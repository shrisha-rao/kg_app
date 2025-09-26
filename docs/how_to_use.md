# How to Use the Research Knowledge Graph Application

This guide will walk you through setting up and using the **Research Knowledge Graph** application on **Google Cloud Platform (GCP)**.

## Prerequisites

1. A **Google Cloud Platform** account with billing enabled.
2. **Terraform** installed on your local machine.
3. **Google Cloud SDK** installed and configured.
4. **Python 3.9+** installed.
5. **Docker** installed (for containerization).

---

## Setup Instructions

### 1. Clone and Initialize the Project

```bash
git clone <your-repository-url>
cd research-kg-app
cp terraform.tfvars.example terraform.tfvars
```

### 2. Configure Terraform Variables

Edit `terraform.tfvars` with your specific values:

```hcl
# Infrastructure Configuration
project_id = "your-gcp-project-id"
region = "us-central1"
environment = "dev" # or "stage" or "prod"

# Application Configuration
app_name = "research-knowledge-graph"
app_version = "1.0.0"

# Database Configuration
arangodb_instance_size = "small" # small, medium, large
redis_memory_size_gb = 1

# LLM Configuration
llm_model = "text-bison@001"
embedding_model = "textembedding-gecko@001"
```

### 3. Set Up GCP Authentication

```bash
gcloud auth login
gcloud config set project your-gcp-project-id
gcloud auth application-default login
```

### 4a. Initialize and Apply Terraform in Bootstrap

Navigate to the `infrastructure/bootstrap` directory and run:

This will create common resources

```bash
cd infrastructure/bootstrap
terraform init
terraform apply -var-file="terraform.tfvars"
```
### 4b. Initialize and Apply Terraform in Dev

```bash
cd infrastructure/dev
terraform init
terraform plan  # Review the plan
terraform apply  # This will create all resources
```

### 5. Build and Deploy the Application

```bash
# Build the Docker image
docker build -t gcr.io/your-gcp-project-id/research-app:latest .

# Push to Google Container Registry
docker push gcr.io/your-gcp-project-id/research-app:latest

# Deploy to Cloud Run (if not using Terraform for deployment)
gcloud run deploy research-knowledge-graph-app \
  --image gcr.io/your-gcp-project-id/research-app:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars "GCP_PROJECT_ID=your-gcp-project-id" \
  --set-env-vars "GCS_BUCKET_NAME=your-bucket-name" \
  # Add other environment variables as needed
```

### 6. Initialize the Knowledge Graph

Run a setup script to initialize the graph database with the necessary collections and indexes:

```bash
python scripts/init_graph_db.py
```

---

## Using the Application

### 1. Access the API

After deployment, you'll receive a Cloud Run URL. The API will be available at:

```
https://your-cloud-run-url.api/v1/
```

### 2. Authentication

The application uses **Firebase Authentication**. You'll need to:

1. Set up **Firebase Authentication** in your GCP project.
2. Configure the **Firebase Admin SDK** in the application.
3. Clients must include an **ID token** in the **Authorization** header.

### 3. Uploading Research Papers

You can upload papers using the API:

```bash
curl -X POST "https://your-cloud-run-url/api/v1/upload" \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -F "file=@path/to/your/paper.pdf" \
  -F "is_public=false" \
  -F "title=Your Paper Title" \
  -F "authors=Author One, Author Two" \
  -F "publication_date=2023-01-01" \
  -F "keywords=keyword1, keyword2"
```

### 4. Querying the Knowledge Graph

You can ask questions about the research papers:

```bash
curl -X POST "https://your-cloud-run-url/api/v1/query" \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the latest findings about quantum computing?",
    "use_public_data": true,
    "use_private_data": true
  }'
```

### 5. Managing Your Library

You can manage your research library through additional API endpoints:

- List your papers: `GET /api/v1/papers`
- Get paper details: `GET /api/v1/papers/{paper_id}`
- Update paper metadata: `PUT /api/v1/papers/{paper_id}`
- Delete a paper: `DELETE /api/v1/papers/{paper_id}`

---

<!-- ## Development Workflow -->

<!-- ### 1. Local Development -->

<!-- ```bash -->
<!-- # Set up a virtual environment -->
<!-- python -m venv venv -->
<!-- source venv/bin/activate  # On Windows: venv -->
