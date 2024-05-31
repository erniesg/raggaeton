import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from raggaeton.backend.src.api.endpoints.agent import create_agent
from raggaeton.backend.src.api.endpoints.tools import create_google_search_tool
from raggaeton.backend.src.utils.common import load_config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

chat_app = FastAPI()


@chat_app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        return {"error": "Query parameter is required"}

    # Load the configuration
    config = load_config()
    tools = [create_google_search_tool()]
    agent = create_agent("openai", tools, config=config, verbose=True)

    def response_stream():
        response = agent.stream_chat(query)
        for token in response.response_gen:
            yield f"data: {token}\n\n"

    return StreamingResponse(response_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(chat_app, host="0.0.0.0", port=8000)
