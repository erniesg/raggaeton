from fastapi import APIRouter, HTTPException
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

    # Determine the function name based on article_type
    function_name = f"generate_draft_{request.article_type}"

    # Call the LLM to get the response and token count
    try:
        response, token_count = llm_handler.call_llm(function_name, request)
    except Exception as e:
        logger.error(f"Error calling LLM handler: {e}")
        raise HTTPException(status_code=500, detail="Error generating draft")

    # Log the LLM response
    logger.info(f"LLM Response: {response}")
    logger.info(f"Token Count: {token_count}")

    return response
