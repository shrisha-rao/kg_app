#src/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.upload import router as upload_router
from src.api.query import router as query_router

# Import clients
from google.cloud import firestore
import redis
from src.services.graph_db.arangodb import ArangoDBService

# -------------------------
# Environment-based configs
# -------------------------
FIRESTORE_EMULATOR_HOST = os.getenv("FIRESTORE_EMULATOR_HOST")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "dev-project")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Firestore client - FIXED VERSION
if FIRESTORE_EMULATOR_HOST:
    # When using emulator, create client without project and credentials
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST
    os.environ[
        "GCLOUD_PROJECT"] = PROJECT_ID  # Set project as environment variable
    #db = firestore.Client(project=PROJECT_ID)
else:
    pass
    # Production: use default credentials
    #db = firestore.Client(project=PROJECT_ID)

# Redis client
# cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# Redis client
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="Research Knowledge Graph API")

# Initialize service instance
graph_db = ArangoDBService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
app.include_router(query_router, prefix="/api/v1", tags=["query"])


# at startup
@app.on_event("startup")
async def startup_event():
    # Check if database is initialized, if not run init script
    from src.scripts.init_graph_db import GraphDBInitializer
    initializer = GraphDBInitializer()
    await initializer.initialize()
    #
    connected = await graph_db.connect()
    if not connected:
        raise RuntimeError("Failed to connect to ArangoDB")
    print("Connected to ArangoDB!")


@app.get("/")
async def root():
    return {"message": "Research Knowledge Graph API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/debug/env")
def debug_env():
    return {
        "ARANGODB_HOST": os.getenv("ARANGODB_HOST"),
        "USE_MOCK_SERVICES": os.getenv("USE_MOCK_SERVICES"),
        "ARANGODB_USERNAME": os.getenv("ARANGODB_USERNAME"),
        "GCP_PROJECT_ID": os.getenv("GCP_PROJECT_ID"),
        "VERTEX_AI_DEPLOYED_INDEX_ID":
        os.getenv("VERTEX_AI_DEPLOYED_INDEX_ID"),
        "NER_EXTRACTION_METHOD": os.getenv("NER_EXTRACTION_METHOD")
    }


@app.on_event("shutdown")
async def shutdown_event():
    await graph_db.disconnect()
    print("Disconnected from ArangoDB!")


# from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
# from fastapi.middleware.cors import CORSMiddleware
# from typing import List
# import json

# from src.config import settings
# from src.services.file_processing import FileProcessingService
# from src.services.query_processing import QueryProcessingService
# from src.api.upload import router as upload_router
# from src.api.query import router as query_router

# app = FastAPI(title="Research Knowledge Graph API")

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Include routers
# app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
# app.include_router(query_router, prefix="/api/v1", tags=["query"])

# @app.get("/")
# async def root():
#     return {"message": "Research Knowledge Graph API"}

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}
