from fastapi import APIRouter, HTTPException
from raggaeton.backend.src.api.services.llm_handler import LLMHandler
from raggaeton.backend.src.schemas.content import (
    EditContentRequest,
    EditContentResponse,
)
from raggaeton.backend.src.utils.common import logger

router = APIRouter()


# No need for a separate EditContentRequestModel, use EditContentRequest directly
@router.post("/edit-content", response_model=EditContentResponse)
async def edit_content(request: EditContentRequest):
    try:
        logger.info(f"Received edit content request: {request.json()}")

        llm_handler = LLMHandler()
        response, token_count = llm_handler.call_llm("edit_content", request)
        logger.info(f"LLM response: {response}")

        return response
    except Exception as e:
        logger.error(f"Error in edit_content endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
