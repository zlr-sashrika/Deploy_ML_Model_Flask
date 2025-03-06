import base64
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import uvicorn
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from devops_agent.agent.devops import DevOpsAgent

# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from devops_agent.db.asyncpostgres import SemiCustomAsyncPostgresSaver
from devops_agent.integrations.devops import do_get_integrations, do_save_integrations
from devops_agent.logs.logging import logger
from devops_agent.rag.devops import (
    embed_bq_docs,
    embed_confluence_docs,
    embed_docker_docs,
    embed_aws_docs,
)
from devops_agent.rag.utils import ConfluenceRequestPayload, RequestPayload
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables
load_dotenv(os.path.join(os.getcwd(), ".env"))

# initialize agent
agent = DevOpsAgent()

# select query for metadata object
SELECT_USER_ID = """
select distinct on (thread_id)
    thread_id,
    COALESCE(jsonb_extract_path_text(metadata, 'writes', '__start__', 'userId'), 'Unknown') AS user_id,
    COALESCE(jsonb_extract_path_text(metadata, 'writes', '__start__', 'messages')::jsonb->0->'kwargs'->>'content', 'Unknown') AS message,
    jsonb_extract_path_text(checkpoint, 'ts') AS created_at
from
    checkpoints
where
    jsonb_extract_path_text(metadata, 'writes', '__start__', 'userId') = %s
order by
    thread_id, created_at desc
limit
    %s
offset
    %s;
"""


async def auth_middleware(request: Request, call_next):
    if not request.url.path.startswith("/copilotkit"):
        return await call_next(request)
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Basic"},
            )
        encoded_credentials = auth_header.split(" ")[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        correct_username = os.getenv("BASIC_AUTH_USERNAME")
        correct_password = os.getenv("BASIC_AUTH_PASSWORD")
        if username != correct_username or password != correct_password:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid credentials"},
                headers={"WWW-Authenticate": "Basic"},
            )
        logger.info(f"Authenticated request from user: {username}")
        return await call_next(request)

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication error"},
            headers={"WWW-Authenticate": "Basic"},
        )


app = FastAPI()
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SemiCustomAsyncPostgresSaver.from_conn_string(
        # "postgresql://kong:kong@127.0.0.1:5432/kong"
        os.getenv("POSTGRES_URL")
    ) as checkpointer:

        if os.getenv("CREATE_SCHEMA", "false").lower() == "true":
            logger.info("Creating schema")
            await checkpointer.setup()

        # Create an async graph
        # await checkpointer.setup()
        graph = await agent.build_graph(checkpointer)

        # Create SDK with the graph
        sdk = CopilotKitRemoteEndpoint(
            agents=[
                LangGraphAgent(
                    name="devops_agent",
                    description="DevOps agent.",
                    graph=graph,
                ),
            ],
        )

        # Add the CopilotKit FastAPI endpoint
        add_fastapi_endpoint(app, sdk, "/copilotkit")
        yield


app.router.lifespan_context = lifespan


async def verify_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic"):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        decoded = base64.b64decode(auth.split()[1]).decode()
        username, password = decoded.split(":", 1)
        correct_username = os.getenv("BASIC_AUTH_USERNAME")
        correct_password = os.getenv("BASIC_AUTH_PASSWORD")
        if username != correct_username or password != correct_password:
            raise ValueError("Invalid username or password")
        return username
    except Exception as e:
        print(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


# Health check route - no authentication required
@app.get("/health")
def health():
    """Health check."""
    return {"status": "Ingested the provided docs on PG Vector Database successfully!"}


# All other routes require authentication
@app.post("/docker_rag")
async def docker_rag(payload: RequestPayload, username: str = Depends(verify_auth)):
    """
    Create Docker RAG with optional reset and data_sources parameters.
    """
    try:
        logger.info(f"User {username} requested Docker RAG: {payload}")
        embed_docker_docs(reset=payload.reset, urls=payload.data_sources)
    except Exception as e:
        logger.error(f"Error in Docker RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "Ingested the provided Docker docs on PG Vector Database successfully!"
    }


@app.post("/bq_rag")
async def bq_rag(payload: RequestPayload, username: str = Depends(verify_auth)):
    """Create BigQuery RAG with optional reset and data_sources parameters."""
    try:
        logger.info(f"User {username} requested BigQuery RAG: {payload}")
        embed_bq_docs(reset=payload.reset, urls=payload.data_sources)
    except Exception as e:
        logger.error(f"Error in BigQuery RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "Ingested the provided BigQuery docs on PG Vector Database successfully!"
    }


@app.post("/aws_rag")
async def aws_rag(payload: RequestPayload, username: str = Depends(verify_auth)):
    """Create AWS RAG with optional reset and data_sources parameters."""
    try:
        logger.info(f"User {username} requested AWS RAG: {payload}")
        embed_aws_docs(
            directory_path=os.getenv("RAG_DATA_PATH", "devops_agent/rag/data/aws/"),
            glob_pattern="./*.md",
            reset=payload.reset,
        )
    except Exception as e:
        logger.error(f"Error in AWS RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "Ingested the provided AWS docs on PG Vector Database successfully!"
    }


@app.post("/embed_confluence_rag")
async def embed_confluence_rag(
    payload: ConfluenceRequestPayload,
    username: str = Depends(verify_auth),
):
    """Embed Confluence documents with optional reset and data_sources parameters."""
    try:
        logger.info(f"User {username} requested Confluence embedding: {payload}")
        embed_confluence_docs(
            reset=payload.reset,
            data_sources=payload.data_sources,
        )
    except Exception as e:
        logger.error(f"Error in embedding Confluence documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "Ingested the provided Confluence docs on PG Vector Database successfully!"
    }


@app.post("/integrations")
async def save_integrations(
    data: List = Body(..., embed=True),
    username: str = Depends(verify_auth),
):
    """Save integrations configuration to file."""
    try:
        logger.info(f"User {username} saving integrations configuration")
        do_save_integrations(data)
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/integrations")
async def get_integrations(username: str = Depends(verify_auth)):
    """Get current integrations configuration."""
    try:
        config = do_get_integrations()
        return {"data": config}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Configuration file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid configuration file format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/{user_id}/threads")
async def get_threads_for_user(
    user_id: str, limit: int = 10, offset: int = 0, username: str = Depends(verify_auth)
):
    """Get conversation threads of a user.
    Args:
        user_id (str): ID of the user.
        limit (int, optional): Page size. Defaults to 10.
        offset (int, optional): Offset after which the page needs to be loaded. Defaults to 0.
    """

    # set user threads
    user_threads = []
    logger.info(f"User {username} requested threads")

    # initialize postgres saver
    async with SemiCustomAsyncPostgresSaver.from_conn_string(
        os.getenv("POSTGRES_URL")
    ) as checkpointer:
        async for tid, uid, msg, cat in checkpointer.get_user_threads(
            SELECT_USER_ID, user_id, limit, offset
        ):
            user_threads.append(
                {"thread_id": tid, "user_id": uid, "message": msg, "created_at": cat}
            )

    # sort by created_at
    user_threads.sort(key=lambda x: x["created_at"], reverse=True)
    return user_threads


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile="/root/.acme.sh/devopsgpt.open-ops.com_ecc/devopsgpt.open-ops.com.key",
            ssl_certfile="/root/.acme.sh/devopsgpt.open-ops.com_ecc/fullchain.cer",
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    port = int(os.getenv("PORT", "8000"))
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile="/root/.acme.sh/devopsgpt.open-ops.com_ecc/devopsgpt.open-ops.com.key",
            ssl_certfile="/root/.acme.sh/devopsgpt.open-ops.com_ecc/fullchain.cer",
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
