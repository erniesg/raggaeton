import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from raggaeton.backend.src.api.endpoints.agent import init_agent  # Import agent
from raggaeton.backend.src.utils.common import config_loader
from contextlib import asynccontextmanager

config_loader._setup_logging()
logger = logging.getLogger(__name__)
# Create FastAPI app
app = FastAPI()


# Create FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan: Initializing components...")

    # Load the agent with the default index path
    agent = init_agent()
    if agent is None:
        logger.error("Agent loading failed. Agent is None.")
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
