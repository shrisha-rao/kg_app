Perfect — here’s a **ready-to-use `.env` setup** for local development vs production, designed so you can switch environments **without changing code or Docker images**.

---

## **1️⃣ `.env.local` (for local dev with emulators)**

```dotenv
# Firestore Emulator
FIRESTORE_EMULATOR_HOST=firestore-emulator:8080
GCP_PROJECT_ID=dev-project

# Redis (local emulator)
REDIS_HOST=redis
REDIS_PORT=6379

# Cloud Storage (can be local minio or just leave empty for dev)
GCS_BUCKET_NAME=dev-research-bucket

# ArangoDB
ARANGODB_HOST=http://arangodb:8529
ARANGODB_USERNAME=root
ARANGODB_PASSWORD=my-secret-password
ARANGODB_DATABASE=test_graph_db
```

---

## **2️⃣ `.env.prod` (for production / Cloud Run)**

```dotenv
# No Firestore emulator in prod
# FIRESTORE_EMULATOR_HOST not set
GCP_PROJECT_ID=your-gcp-project-id

# Redis (GCP Memorystore IP)
REDIS_HOST=<memstore-ip>
REDIS_PORT=6379

# Cloud Storage
GCS_BUCKET_NAME=your-prod-bucket-name

# ArangoDB (if used in prod)
ARANGODB_HOST=<arangodb-prod-host>
ARANGODB_USERNAME=<username>
ARANGODB_PASSWORD=<password>
ARANGODB_DATABASE=prod_graph_db
```

---

## **3️⃣ How to switch environments**

* **Local dev:**

```bash
cp .env.local .env
docker-compose up --build
```

* **Production / Cloud Run:**

```bash
cp .env.prod .env
docker build -t research-app .
# deploy the same container to Cloud Run
gcloud run deploy research-app \
  --image gcr.io/your-project-id/research-app \
  --set-env-vars-file=.env.prod \
  --region us-central1 \
  --platform managed
```

---

### ✅ Benefits

1. No code changes when switching from **local** → **cloud**.
2. Same Docker image works in **both environments**.
3. Firestore emulator and Redis locally allow **cheap, fast testing**.
4. Environment variables handle configuration cleanly.

---

If you want, I can also provide a **full updated `docker-compose.yml` with `.env.local` integration**, so running `docker-compose up` automatically picks up all emulators and services correctly.

Do you want me to do that?
