import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from modal import App, Image, asgi_app, Secret, Mount
import os
import sys
import modal.exception
from starlette.requests import ClientDisconnect
import pickle

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress specific debug loggers
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Create FastAPI app
fastapi_app = FastAPI()

# Global variables to store the initialized components
config = None
tools = None


# Define the Modal image with necessary dependencies
def initialize_components():
    global config, tools
    logger.info("Initializing components...")
    sys.path.insert(0, "/app/raggaeton")
    from raggaeton.backend.src.api.endpoints.agent import initialize_agent

    agent = initialize_agent()  # Initialize the agent here
    logger.info("Components initialized successfully")
    # Pickle the agent
    with open("/app/raggaeton/agent.pkl", "wb") as f:
        pickle.dump(agent, f)

    return agent


chat_image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
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
    .apt_install("git")  # Ensure git is installed
    .run_function(
        initialize_components,
        secrets=[
            Secret.from_name("my-postgres-secret"),
            Secret.from_name("my-openai-secret"),
        ],
        mounts=[Mount.from_local_python_packages("raggaeton")],
    )
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


@app.function(mounts=[raggaeton_mount], timeout=300)
@asgi_app(label="raggaeton")
def serve_chat_app():
    global agent
    logger.info("Starting ASGI app...")

    # Load the pickled agent
    try:
        with open("/app/raggaeton/agent.pkl", "rb") as f:
            agent = pickle.load(f)
        logger.info(f"Agent loaded successfully and is of type: {type(agent)}")
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")

    return fastapi_app


@fastapi_app.post("/chat")
async def chat(request: Request):
    logger.info("Received request at /chat endpoint")

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

    def response_stream():
        response = agent.stream_chat(query)
        for token in response.response_gen:
            print(token, end="")
            yield token.encode()

    return StreamingResponse(response_stream(), media_type="text/event-stream")


@app.local_entrypoint()
def main():
    logger.info("Running local entrypoint...")
    try:
        serve_chat_app.remote()
    except modal.exception.FunctionTimeoutError:
        logger.error("Function execution timed out.")


# Ensure main is called when the script is executed
if __name__ == "__main__":
    main()
# from fastapi import FastAPI, Request
# from fastapi.responses import StreamingResponse
# from contextlib import asynccontextmanager
# from modal import App, Image, asgi_app, Secret, Mount
# import logging
# import modal.exception
# from starlette.requests import ClientDisconnect
# from raggaeton.backend.src.api.endpoints.agent import initialize_agent, agent

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Suppress specific debug loggers
# logging.getLogger("hpack").setLevel(logging.WARNING)
# logging.getLogger("httpx").setLevel(logging.WARNING)

# # Define the Modal image with necessary dependencies and mount the local package
# chat_image = (
#     Image.debian_slim(python_version="3.10")
#     .apt_install("git")  # Ensure git is installed
#     .pip_install(
#         "requests",
#         "supabase",
#         "PyYAML",
#         "python-dotenv",
#         "llama-index",
#         "llama-index-readers-database",
#         "llama-index-embeddings-huggingface",
#         "llama-index-vector-stores-supabase",
#         "llama-index-callbacks-deepeval",
#         "psycopg2-binary",
#         "deepeval",
#         "llama-index-tools-google",
#         "llama-index-callbacks-arize-phoenix",
#         "arize-phoenix[evals]",
#         "llama-index-packs-ragatouille-retriever",
#         "ragatouille",
#         "fastapi",
#         "uvicorn",
#     )
# )

# # Define the Modal app
# app = App(
#     name="raggaeton-chat-app",
#     image=chat_image,
#     secrets=[
#         Secret.from_name("my-supabase-secret"),
#         Secret.from_name("my-openai-secret"),
#         Secret.from_name("my-search-secret"),
#         Secret.from_name("my-anthropic-secret"),
#         Secret.from_name("my-postgres-secret"),
#     ],
#     mounts=[Mount.from_local_python_packages("raggaeton")],  # Add the mount here
# )


# # Define the lifespan context manager
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     logger.info("Lifespan context manager: Initializing components...")
#     global agent
#     agent = initialize_agent()  # Initialize the agent here
#     logger.info("Lifespan context manager: Components initialized")
#     yield
#     logger.info("Lifespan context manager: Cleaning up resources if needed")


# # Create FastAPI app with lifespan
# fastapi_app = FastAPI(lifespan=lifespan)


# @app.function(timeout=300)
# @asgi_app(label="raggaeton")
# def serve_chat_app():
#     global agent

#     logger.info("Starting ASGI app...")
#     if agent is None:
#         logger.info("Agent is not initialized. Initializing now...")
#         agent = initialize_agent()
#     return fastapi_app


# @fastapi_app.post("/chat")
# async def chat(request: Request):
#     logger.info("Received request at /chat endpoint")

#     try:
#         data = await request.json()
#     except ClientDisconnect:
#         logger.error("Client disconnected before request could be read")
#         return {"error": "Client disconnected"}
#     except Exception as e:
#         logger.error(f"Error reading request data: {e}")
#         raise

#     query = data.get("query")
#     if not query:
#         logger.error("Query parameter is required")
#         return {"error": "Query parameter is required"}

#     if agent is None:
#         logger.error("Agent is not initialized.")
#         return {"error": "Agent is not initialized"}

#     def response_stream():
#         response = agent.stream_chat(query)
#         for token in response.response_gen:
#             print(token, end="")
#             yield token.encode()

#     return StreamingResponse(response_stream(), media_type="text/event-stream")


# @app.local_entrypoint()
# def main():
#     logger.info("Running local entrypoint...")
#     try:
#         serve_chat_app.remote()

#     except modal.exception.FunctionTimeoutError:
#         logger.error("Function execution timed out.")


# # Ensure main is called when the script is executed
# if __name__ == "__main__":
#     main()
