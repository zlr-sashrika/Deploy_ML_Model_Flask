
## Devops GPT local development setup

### Pre-requisites

- Install [Docker](https://docs.docker.com/get-docker/)
- Install Python `3.12.3` (with [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation))

    ```
    curl -fsSL https://pyenv.run | bash
    pyenv install 3.12.3
    pyenv global 3.12.3
    ```

- Install [Poetry](https://python-poetry.org/docs/)

    ```
    curl -sSL https://install.python-poetry.org | python -
    ``` 

### Install dependencies and run the app
- Clone the repo
    ```
    git clone https://github.com/zelarhq/langgraph-examples.git
    cd langgraph-examples/copilotkit-agent
    ```
- Activate the virtual environment
    ```
    poetry shell
    ```
- Install dependencies
    ```
    poetry install
    ```

-   Create a `.env` file from `.env.example`

    ```
    cp .env.example .env
    ```
    > Update the `.env` file with your own values

 - BThe backend APIs are protected and require Basic Authentication to access the endpoints. Set up the following environment variables in the .env file

  ```plaintext
  BASIC_AUTH_USERNAME
  BASIC_AUTH_PASSWORD
  ``

- Start the Database

    ```
    docker compose up -d
    ```

- Run the app

    ```
    poetry run devops_agent
    ```

### Next: Go to the frontend repo [devopsgpt.io](https://github.com/zelarhq/devopsgpt.io) and run it to see the app in action in the browser


>**NOTE**: Disregard all the following instructions. They are for production.


- Build the binary for production

    ```
    pyinstaller --onefile app.py --distpath devops_agent/bin/.dist/ --specpath devops_agent/bin/ --workpath devops_agent/bin/.build/ --hidden-import=pydantic.deprecated.decorator
    ```

-   Execute the binary

    ```
    devops_agent/bin/.dist/app
    ```

- Create a systemd service (for production)

    ```
    [Unit]
    Description=LangGraph CopilotKit Agent Service
    After=network.target

    [Service]
    Type=simple
    User=root
    WorkingDirectory=/root/langgraph-examples/copilotkit-agent
    ExecStart=/bin/bash -c 'source langg/bin/activate && poetry run demo'
    Restart=on-failure
    Environment="PATH=/usr/local/bin:/usr/bin:/bin:/snap/bin"

    [Install]
    WantedBy=multi-user.target
    ```

- Run the app in production
    ```
    docker run -d --security-opt seccomp=unconfined --security-opt apparmor=unconfined -v /sys/fs/cgroup:/sys/fs/cgroup -e STORAGE_DRIVER=vfs -e BUILDAH_FORMAT=docker -e BUILDAH_ISOLATION=chroot -p 8002:8000 --env-file=.env -v /root/.acme.sh/devopsgpt.open-ops.com_ecc:/root/.acme.sh/devopsgpt.open-ops.com_ecc
    ```

### API Endpoints

#### Call the Docker RAG endpoint
Create Docker RAG with optional `reset` and `data_sources` parameters.

- **URL**: `/docker_rag`
- **Method**: `POST`
- **Parameters**:
  - `reset` (boolean, optional): If `true`, clears the data from the vector store.
  - `data_sources` (list of strings, optional): URLs to connect to.

Example:
```sh
curl -X POST http://localhost:8000/docker_rag \
  -H "Content-Type: application/json" \
  -d '{
        "reset": true,
        "data_sources": ["https://my-url1.com", "https://my-url2.com"]
      }'
```

#### Call the BigQuery RAG endpoint
Create BigQuery RAG with optional `reset` and `data_sources` parameters.

- **URL**: `/bq_rag`
- **Method**: `POST`
- **Parameters**:
  - `reset` (boolean, optional): If `true`, clears the data from the vector store.
  - `data_sources` (list of strings, optional): URLs to connect to.

Example:
```sh
curl -X POST http://localhost:8000/bq_rag \
  -H "Content-Type: application/json" \
  -d '{
        "reset": true,
        "data_sources": ["https://my-url1.com", "https://my-url2.com"]
      }'
```

#### Call the Embed Confluence RAG endpoint
Embed Confluence documents with optional `reset`, `space`, and `page_ids` parameters. Either `space` or `page_ids` is mandatory.

- **URL**: `/embed_confluence_rag`
- **Method**: `POST`
- **Parameters**:
  - `reset` (boolean, optional): If `true`, clears the data from the vector store.
  - `space` (string, optional): Confluence space to embed.
  - `page_ids` (list of strings, optional): Confluence page IDs to embed.

Example:
```sh
curl -X POST http://localhost:8000/embed_confluence_rag \
  -H "Content-Type: application/json" \
  -d '{
        "reset": true,
        "space": "my-space",
        "page_ids": ["12345", "67890"]
      }'
```