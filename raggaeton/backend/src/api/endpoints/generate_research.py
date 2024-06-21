from fastapi import APIRouter
from raggaeton.backend.src.schemas.research import (
    GenerateResearchQuestionsRequest,
    DoResearchRequest,
    GenerateResearchQuestionsResponse,
    DoResearchResponse,
)
from raggaeton.backend.src.api.services.llm_handler import LLMHandler
from raggaeton.backend.src.api.services.fetch import (
    fetch_data_from_you,
    fetch_data_from_wikipedia,
    fetch_data_from_obsidian,
)
from raggaeton.backend.src.api.services.prompts import get_prompts
from raggaeton.backend.src.utils.common import (
    logger,
    error_handling_context,
    config_loader,
)

router = APIRouter()


@router.post(
    "/generate-research-questions", response_model=GenerateResearchQuestionsResponse
)
async def generate_research_questions(request: GenerateResearchQuestionsRequest):
    logger.info(
        f"Received generate-research-questions request: {request.model_dump_json()}"
    )
    llm_handler = LLMHandler()
    with error_handling_context():
        system_prompt, message_prompt = get_prompts(
            "generate_research_questions", request
        )
        response_text, token_count = llm_handler.call_llm(
            "generate_research_questions", request
        )
        logger.info(f"Type of response_text: {type(response_text)}")

        # Ensure response_text is a valid JSON string
        if isinstance(response_text, str):
            response_text = GenerateResearchQuestionsResponse.model_validate_json(
                response_text
            )

        return response_text


@router.post("/do-research", response_model=DoResearchResponse)
async def do_research(request: DoResearchRequest):
    logger.info(f"Received do-research request: {request.model_dump_json()}")
    with error_handling_context():
        research_results = {}
        for platform_data in request.research_questions:
            platform = platform_data["platform"]
            keywords = platform_data["keywords"]
            if platform == "you.com":
                research_results[platform] = fetch_data_from_you(
                    keywords, limit=request.optional_params.desired_length
                )
            elif platform == "wikipedia":
                research_results[platform] = fetch_data_from_wikipedia(
                    keywords, limit=request.optional_params.desired_length
                )
            elif platform == "obsidian":
                obsidian_vault_path = config_loader.config["obsidian_vault"]
                research_results[platform] = fetch_data_from_obsidian(
                    obsidian_vault_path, author="John Doe"
                )
            # Add more platforms as needed
        return DoResearchResponse(fetched_research=research_results)
