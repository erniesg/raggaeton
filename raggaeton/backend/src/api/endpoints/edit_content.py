from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from raggaeton.backend.src.api.services.llm_handler import LLMHandler
from raggaeton.backend.src.schemas.content import (
    EditContentRequest,
    EditContentResponse,
)
from raggaeton.backend.src.utils.common import logger

router = APIRouter()


class EditContentRequestModel(BaseModel):
    request: EditContentRequest


@router.post("/edit_content", response_model=EditContentResponse)
async def edit_content(request: EditContentRequestModel):
    try:
        llm_handler = LLMHandler()
        response, token_count = llm_handler.call_llm("edit_content", request.request)
        return response
    except Exception as e:
        logger.error(f"Error in edit_content endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
