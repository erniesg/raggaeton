from fastapi import APIRouter
from raggaeton.backend.src.schemas.content import (
    GenerateHeadlinesRequest,
    GenerateHeadlinesResponse,
    Headline,
)
from raggaeton.backend.src.api.services.llm_handler import LLMHandler
from raggaeton.backend.src.api.services.prompts import get_prompts
from raggaeton.backend.src.utils.common import logger, error_handling_context

router = APIRouter()


@router.post("/generate-headlines", response_model=GenerateHeadlinesResponse)
async def generate_headlines(request: GenerateHeadlinesRequest):
    logger.debug("Received request to generate headlines")  # Add this line

    system_prompt, message_prompt = get_prompts("generate_headlines", request)

    llm_handler = LLMHandler()
    with error_handling_context():
        response_text, token_count = llm_handler.call_llm(
            "generate_headlines",
            request,
            system_prompt=system_prompt,
            message_prompt=message_prompt,
        )

        # Use the centralized logger from common.py
        logger.info(f"response_text.headlines: {response_text.headlines}")

        # Directly use the Headline objects if they are already in the correct form
        headlines = [
            headline if isinstance(headline, Headline) else Headline(**headline)
            for headline in response_text.headlines
        ]
        logger.debug(f"Generated headlines: {headlines}")  # Add this line

        return GenerateHeadlinesResponse(headlines=headlines)
