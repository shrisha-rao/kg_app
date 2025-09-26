#!/bin/bash 
# gcloud components install cloud-firestore-emulator
# gcloud beta emulators firestore start --host-port=localhost:8080
# export FIRESTORE_EMULATOR_HOST=localhost:8080
# export GOOGLE_CLOUD_PROJECT=dev-project

# In Docker, you can pass this as env vars:
# ENV FIRESTORE_EMULATOR_HOST=host.docker.internal:8080
# ENV GOOGLE_CLOUD_PROJECT=dev-project

# TEST emulator
# from google.cloud import firestore
# db = firestore.Client()
# doc_ref = db.collection("test").document("abc")
# doc_ref.set({"hello": "world"})
# print(doc_ref.get().to_dict())

# --------------
# REDIS
# --------------
# On Mac
# brew install redis
# brew services start redis

# On Linux
# sudo apt update
# sudo apt install redis-server
# sudo systemctl enable redis-server
# sudo systemctl start redis-server

# REDIS_HOST=localhost
# REDIS_PORT=6379

# TEST redis emulator
# import redis
# r = redis.Redis(host="localhost", port=6379, db=0)
# r.set("key", "value")
# print(r.get("key"))


# Make sure .env.local exists
# docker-compose up --build

# When deploying to Cloud Run or GCP, just replace .env.local with .env.prod and remove the emulator services. The same Docker images work without code changes.

# FastAPI: http://localhost:8000
# Jupyter: http://localhost:8888
# Firestore Emulator: localhost:8080
# Redis: localhost:6379
# ArangoDB: localhost:8529
