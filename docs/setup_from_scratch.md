# Create GCP Project

## Apply Steps

To set up your infrastructure, follow these steps:

1. Navigate to the bootstrap directory:
   ```bash
   cd infrastructure/bootstrap
   ```

2. Initialize Terraform:
   ```bash
   terraform init
   ```

3. Apply the Terraform configuration:
   ```bash
   terraform apply -var-file="terraform.tfvars"
   ```

After the project is created, make sure to:

- Remove or stop managing the **google_project** resource in the environment configurations.
- Set each environment's **project_id** to the created project.
