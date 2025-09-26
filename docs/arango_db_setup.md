## Running ArangoDB locally

run ArangoDB locally for development and testing. The most common and recommended way to do this is by using **Docker**, as it provides an isolated, portable, and easy-to-manage environment.

---

### Setting Up ArangoDB Locally

Using Docker is the most straightforward method. It eliminates the need for a full installation on your host machine and ensures your environment is consistent.

#### 1. Install Docker

First, ensure you have **Docker Desktop** installed on your system (Windows, macOS, or Linux). This will give you the Docker engine and the Docker CLI.

#### 2. Run the ArangoDB Container

Open your terminal or command prompt and execute the following command:

```bash
docker run -e ARANGO_ROOT_PASSWORD=my-secret-password -p 8529:8529 -d --name arangodb arangodb/arangodb
```

Let's break this down:

- `docker run`: The command to run a new container.  
- `-e ARANGO_ROOT_PASSWORD=my-secret-password`: Sets an environment variable to define the root password for your ArangoDB instance. You **must** provide a password or disable authentication.  
- `-p 8529:8529`: Maps port **8529** from the container to port **8529** on your local machine. This is the default port for ArangoDB.  
- `-d`: Runs the container in **detached mode**, so it runs in the background.  
- `--name arangodb`: Assigns a name to your container for easy reference.  
- `arangodb/arangodb`: The name of the official Docker image for ArangoDB.

After running this command, ArangoDB will be running locally. You can access it via the web interface at `http://localhost:8529` using the username `root` and the password you set.

---

### How to Use Your Script to Set Up the Database

Your provided `init_graph_db.py` script is a perfect example of a script designed to be run against a locally-hosted ArangoDB instance. To use it, you need to ensure your Python environment has the necessary libraries and is configured correctly.

#### 1. Install the Python Driver

Your script uses a `get_graph_db_service` function, which likely relies on a Python client for ArangoDB. The most common one is `python-arango`.

```bash
pip install python-arango
```

#### 2. Configure the Connection

Your script imports `settings` from `src.config`. This file likely contains the connection details for your database, such as the host, port, username, and password. You'll need to update this file to match your local setup.

Example `src/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ARANGODB_HOST: str = "http://localhost:8529"
    ARANGODB_USER: str = "root"
    ARANGODB_PASSWORD: str = "my-secret-password"
    ARANGODB_DB: str = "_system"

    class Config:
        env_file = ".env"

settings = Settings()
```

Make sure the `ARANGODB_PASSWORD` matches the password you set when running the Docker container.

#### 3. Run the Initialization Script

Once your Docker container is running and your configuration is set up, you can execute your Python script from the root directory of your project:

```bash
python scripts/init_graph_db.py
```

```bash
docker run --rm \
    --network "$NETWORK_NAME" \
    -v "$APP_DIR":/app \
    -w /app \
> -it "$TESTER_IMAGE" /bin/bash
```

The script will:

- Connect to the ArangoDB instance you started with Docker.  
- Create the specified **node collections** (`nodes_paper`, `nodes_person`, etc.).  
- Create the specified **edge collections** (`edges_cites`, `edges_authored_by`, etc.).  
- Define and create the **knowledge graph** with the relationships you've specified.  
- Create **persistent indexes** on the collections for improved query performance.

If successful, you will see a `🎉 Graph database initialization completed successfully!` message in your terminal. You can then use the ArangoDB web interface to verify that all the collections and the graph have been created as expected.
