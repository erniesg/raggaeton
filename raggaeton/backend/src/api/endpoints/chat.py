import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from raggaeton.backend.src.api.endpoints.agent import get_agent
from raggaeton.backend.src.utils.common import config_loader
from raggaeton.backend.src.utils.error_handler import (
    error_handling_context,
    InitializationError,
)
from contextlib import asynccontextmanager
import os

config_loader._setup_logging()
logger = logging.getLogger(__name__)
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware to catch and handle exceptions globally
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    with error_handling_context():
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan: Initializing components...")

    # Log contents of the index directory
    index_path = "/app/.ragatouille/colbert/indexes/my_index"
    if os.path.exists(index_path):
        logger.info(f"Index path exists: {index_path}")
    else:
        logger.error(f"Index path does not exist: {index_path}")

    # Load the agent with the default index path
    logger.info("Calling get_agent...")

    agent = get_agent(index_path=index_path)
    if agent is None:
        raise InitializationError("Agent loading failed. Agent is None.")
    else:
        logger.info(f"Agent loaded successfully: {type(agent)}")

    app.state.agent = agent  # Store the agent in the app state
    logger.info("Lifespan: Components initialized successfully")

    yield


app = FastAPI(lifespan=lifespan)


@app.post("/chat")
async def chat(request: Request):
    logger.info("Received request at /chat endpoint")

    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Error reading request data: {e}")
        return {"error": "Error reading request data"}

    query = data.get("query")
    if not query:
        logger.error("Query parameter is required")
        return {"error": "Query parameter is required"}
    if app.state.agent is None:
        logger.error("Agent is not initialized.")
        return {"error": "Agent is not initialized"}

    def response_stream():
        response = app.state.agent.stream_chat(
            query
        )  # Access the agent from the app state
        for token in response.response_gen:
            yield token.encode()

    return StreamingResponse(response_stream(), media_type="text/event-stream")
