# check_index_content.py
from google.cloud import aiplatform


def check_if_index_has_data():
    """Check if the index actually contains any vectors"""
    PROJECT_ID = "kg-app-473211"
    LOCATION = "us-central1"
    INDEX_ENDPOINT_ID = "projects/kg-app-473211/locations/us-central1/indexEndpoints/4538311209459384320"
    DEPLOYED_INDEX_ID = "research_deployed_index_v1"

    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    endpoint = aiplatform.MatchingEngineIndexEndpoint(
        index_endpoint_name=INDEX_ENDPOINT_ID)

    # Try a random query to see if we get any results
    test_query = [0.0] * 384  # Zero vector

    try:
        response = endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[test_query],
            num_neighbors=1  # Just check if there's ANY data
        )

        if response and len(response) > 0 and len(response[0]) > 0:
            print("✅ Index contains data!")
            print(f"Found {len(response[0])} vectors")
            return True
        else:
            print("❌ Index appears to be empty")
            return False

    except Exception as e:
        print(f"❌ Error checking index: {e}")
        return False


if __name__ == "__main__":
    check_if_index_has_data()
