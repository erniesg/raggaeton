from fastapi import APIRouter
from raggaeton.backend.src.schemas.content import (
    GenerateDraftRequest,
    GenerateDraftResponse,
)
from raggaeton.backend.src.utils.common import logger  # Import logger
from raggaeton.backend.src.api.services.llm_handler import LLMHandler

router = APIRouter()


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(request: GenerateDraftRequest):
    # Log the incoming request
    logger.info(f"Received request: {request}")

    # Initialize the LLM handler
    llm_handler = LLMHandler()

    # Call the LLM to get the response and token count
    response, token_count = llm_handler.call_llm("generate_draft_benefits", request)

    # Log the LLM response
    logger.info(f"LLM Response: {response}")
    logger.info(f"Token Count: {token_count}")

    return response
