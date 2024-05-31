import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from modal import App, Image, asgi_app, Secret, Mount
import os
import sys
import modal.exception
from starlette.requests import ClientDisconnect

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress specific debug loggers
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Define the Modal image with necessary dependencies
chat_image = Image.debian_slim(python_version="3.10").pip_install(
    "requests",
    "supabase",
    "PyYAML",
    "python-dotenv",
    "llama-index",
    "llama-index-readers-database",
    "llama-index-embeddings-huggingface",
    "llama-index-vector-stores-supabase",
    "llama-index-callbacks-deepeval",
    "psycopg2-binary",
    "deepeval",
    "llama-index-tools-google",
    "llama-index-callbacks-arize-phoenix",
    "arize-phoenix[evals]",
    "llama-index-packs-ragatouille-retriever",
    "ragatouille",
    "fastapi",
    "uvicorn",
)

# Define the Modal app
app = App(
    name="raggaeton-chat-app",
    image=chat_image,
    secrets=[
        Secret.from_name("my-supabase-secret"),
        Secret.from_name("my-openai-secret"),
        Secret.from_name("my-search-secret"),
        Secret.from_name("my-anthropic-secret"),
        Secret.from_name("my-postgres-secret"),
    ],
)

# Mount the local directory
raggaeton_mount = Mount.from_local_dir(
    local_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
    remote_path="/app/raggaeton",
    condition=lambda pth: not pth.endswith(".env")
    and not pth.endswith("modal_chat.py"),
    recursive=True,
)

# Create FastAPI app
fastapi_app = FastAPI()


@fastapi_app.post("/chat")
async def chat(request: Request):
    logger.info("Received request at /chat endpoint")
    sys.path.insert(0, "/app/raggaeton")

    from raggaeton.backend.src.api.endpoints.agent import create_agent
    from raggaeton.backend.src.api.endpoints.tools import create_google_search_tool
    from raggaeton.backend.src.utils.common import load_config

    try:
        data = await request.json()
    except ClientDisconnect:
        logger.error("Client disconnected before request could be read")
        return {"error": "Client disconnected"}
    except Exception as e:
        logger.error(f"Error reading request data: {e}")
        raise

    query = data.get("query")
    if not query:
        logger.error("Query parameter is required")
        return {"error": "Query parameter is required"}

    config = load_config()

    tools = [create_google_search_tool()]
    agent = create_agent("openai", tools, config=config, verbose=True)

    def response_stream():
        response = agent.stream_chat(query)
        for token in response.response_gen:
            print(token, end="")
            yield token.encode()

    return StreamingResponse(response_stream(), media_type="text/event-stream")


@app.function(mounts=[raggaeton_mount], timeout=300)  # Set timeout to 300 seconds
@asgi_app(label="raggaeton")
def serve_chat_app():
    return fastapi_app


@app.local_entrypoint()
def main():
    try:
        serve_chat_app.remote()
    except modal.exception.FunctionTimeoutError:
        logger.error("Function execution timed out.")
