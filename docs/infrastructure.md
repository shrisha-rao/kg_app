
---

### 📄 `infrastructure.md`

```markdown
# Research Knowledge Graph Infrastructure

This Terraform configuration deploys the Google Cloud resources needed for the **Research Knowledge Graph application**.  
It provisions storage, Firestore, Vertex AI indexes, Redis (Memorystore), Cloud Run, and all required IAM bindings.

---

## 📂 Project Structure

```

terraform/
├── main.tf        # resources
├── provider.tf    # provider configuration
├── variables.tf   # input variables
├── outputs.tf     # outputs
├── locals.tf      # local constants
├── versions.tf    # version constraints

````

---

## ⚙️ Prerequisites

- [Terraform >= 1.5](https://developer.hashicorp.com/terraform/downloads)
- A Google Cloud project with billing enabled
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated with sufficient permissions

Enable the required APIs:

```sh
gcloud services enable \
  compute.googleapis.com \
  iam.googleapis.com \
  run.googleapis.com \
  redis.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com
````

---

## 🚀 Usage

### 1. Initialize Terraform

```sh
terraform init
```

### 2. Set Variables

You must provide:

* `project_id` (your GCP project ID)
* `region` (deployment region, e.g. `us-central1`)

Options:

* Pass inline with `-var`:

  ```sh
  terraform apply -var="project_id=my-project" -var="region=us-central1"
  ```
* Or create a `terraform.tfvars` file:

  ```hcl
  project_id = "my-project"
  region     = "us-central1"
  ```

### 3. Plan Changes

```sh
terraform plan
```

### 4. Apply Changes

```sh
terraform apply
```

---

## 📦 Outputs

After `terraform apply`, you’ll see:

* `cloud_run_url` → Public URL of the Cloud Run service
* `redis_host` → Internal Redis host (accessible via VPC connector)

---

## 📝 Notes

* Firestore can **only exist in one region per project**. Ensure `var.region` is Firestore-supported.
* Memorystore (Redis) is deployed in the **default VPC**.
* Cloud Run uses a **Serverless VPC Access connector** to reach Redis.
* The Vertex AI Index uses a **stable ID (`research-index-v1`)**. Update `locals.tf` to bump versions.

---

## 🔐 Security

* Cloud Run is made **publicly accessible** via IAM binding (`allUsers`).
* If you want to restrict access, remove the `google_cloud_run_service_iam_member.public_access` resource.
* Memorystore Redis does **not use AUTH by default** — if stronger security is required, consider alternative caching solutions or private-only access.
