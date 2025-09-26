# Create the service account (if it doesn't exist)

PROJECT="kg-app-473211"

gcloud config set project $PROJECT
gcloud auth application-default set-quota-project $PROJECT

gcloud iam service-accounts create research-graph-processor \
    --description="Service account for Research Graph application" \
    --display-name="Research Graph Processor"

# Grant necessary roles Vertex AI permissions
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:research-graph-processor@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Grant Datastore permissions
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:research-graph-processor@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:research-graph-processor@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Generate and download the key file
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=research-graph-processor@$PROJECT.iam.gserviceaccount.com


# Grant 
gcloud projects add-iam-policy-binding kg-app-473211 \
    --member="serviceAccount:research-graph-processor@kg-app-473211.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"


gcloud projects add-iam-policy-binding kg-app-473211 \
    --member="serviceAccount:research-graph-processor@kg-app-473211.iam.gserviceaccount.com" \
    --role="roles/datastore.user"
