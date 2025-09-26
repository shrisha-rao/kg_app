# Local Deployment for Development and Testing

This guide will help you set up a local deployment of the **Research Knowledge Graph** application for development and testing purposes.

## Prerequisites

1. **Docker** installed on your machine.
2. **Python 3.9+** installed (if you need to run scripts locally).

---

## Local Deployment Instructions

### 1. Set Up a Local Environment

Ensure you have Docker installed on your machine. You may also want to set up a virtual environment for Python dependencies if you plan to run any Python scripts locally.

### 2. Create a Local Configuration

You may want to create a separate configuration file for local development, including local database settings and other environment-specific variables.

### 3. Build the Docker Image Locally

Navigate to the project directory and build the Docker image:

```bash
cd research-kg-app
docker build -t research-app:latest .
```

### 4. Run the Docker Container Locally

Run the Docker container with the necessary environment variables:

```bash
docker run -d \
  -p 8000:8000 \
  -e GCP_PROJECT_ID="your-local-project-id" \
  -e GCS_BUCKET_NAME="your-local-bucket-name" \
  research-app:latest
```

This command maps port 8000 of your local machine to port 8000 of the container, allowing you to access the application via `http://localhost:8000`.

### 5. Initialize the Knowledge Graph Locally

If your application requires initializing the graph database, you can run the initialization script inside the container or directly on your local machine:

```bash
python src/scripts/init_graph_db.py
```

### 6. Access the Application Locally

After running the Docker container, you can access the application at:

```
http://localhost:8000/api/v1/
```

### 7. Testing Locally

You can use tools like **Postman** or **curl** to test the API endpoints locally. For example, to upload a research paper:

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@path/to/your/paper.pdf" \
  -F "is_public=false" \
  -F "title=Your Paper Title" \
  -F "authors=Author One, Author Two" \
  -F "publication_date=2023-01-01" \
  -F "keywords=keyword1, keyword2"
```

### 8. Stopping the Local Deployment

To stop the Docker container, you can use:

```bash
docker ps  # Get the container ID
docker stop <container_id>
```

---

This local deployment setup allows you to test and develop the Research Knowledge Graph application efficiently before deploying it to Google Cloud Platform.
