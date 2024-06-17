from pydantic import BaseModel, ValidationError
from raggaeton.backend.src.schemas.research import GenerateResearchQuestionsResponse
from raggaeton.backend.src.schemas.content import (
    GenerateHeadlinesResponse,
    GenerateDraftResponse,
)
from raggaeton.backend.src.utils.common import logger
from raggaeton.backend.src.utils.error_handler import error_handling_context
import json


def parse_llm_response(
    response_content: str, request_type: str, request_data: dict
) -> BaseModel:
    logger.info("Entered parse_llm_response function")
    logger.info(
        f"Parsing response content: {response_content[:500]}..."
    )  # Log the first 500 characters of the response

    if not isinstance(response_content, str):
        logger.error(
            f"Expected response_content to be a str, but got {type(response_content)}"
        )
        raise TypeError(
            f"Expected response_content to be a str, but got {type(response_content)}"
        )

    # Log the entire response content for debugging
    logger.debug(f"Full response content: {response_content}")

    # Validate JSON manually
    try:
        json_data = json.loads(response_content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        raise

    with error_handling_context():
        if request_type == "generate_research_questions":
            try:
                logger.info(
                    "Attempting to parse JSON into GenerateResearchQuestionsResponse model"
                )
                transformed_response = (
                    GenerateResearchQuestionsResponse.model_validate_json(
                        json.dumps(json_data)
                    )
                )
                logger.info(
                    "Successfully parsed response into GenerateResearchQuestionsResponse model"
                )
                return transformed_response
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                raise
            except Exception as e:
                logger.error(f"Error parsing JSON response: {e}")
                raise
        elif request_type == "generate_headlines":
            try:
                logger.info(
                    "Attempting to parse JSON into GenerateHeadlinesResponse model"
                )
                transformed_response = GenerateHeadlinesResponse.model_validate_json(
                    json.dumps(json_data)
                )
                logger.info(
                    "Successfully parsed response into GenerateHeadlinesResponse model"
                )
                return transformed_response
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                raise
            except Exception as e:
                logger.error(f"Error parsing JSON response: {e}")
                raise
        elif request_type.startswith("generate_draft_"):
            try:
                logger.info(
                    f"Attempting to parse JSON into GenerateDraftResponse model for {request_type}"
                )

                # Transform the response to include the 'drafts' field if it is missing
                if "drafts" not in json_data:
                    json_data = {
                        "drafts": [
                            {
                                "headline": request_data.get("headline"),
                                "hook": request_data.get("hook"),
                                "thesis": request_data.get("thesis"),
                                "article_type": request_data.get("article_type"),
                                "structure": [
                                    {
                                        "content_block": block["content_block"],
                                        "details": block["details"]
                                        if isinstance(block["details"], str)
                                        else " ".join(
                                            str(item) for item in block["details"]
                                        )
                                        if isinstance(block["details"], list)
                                        else json.dumps(block["details"]),
                                    }
                                    for block in json_data.get("structure", [])
                                ],
                                "optional_params": request_data.get(
                                    "optional_params", {}
                                ),
                            }
                        ]
                    }

                # Ensure 'details' is a string
                for draft in json_data.get("drafts", []):
                    for block in draft.get("structure", []):
                        logger.debug(
                            f"Original details for block {block['content_block']}: {block['details']}"
                        )
                        logger.debug(
                            f"Type of details: {type(block['details'])}, Content of details: {block['details']}"
                        )
                        if isinstance(block["details"], list):
                            block["details"] = " ".join(
                                str(item) for item in block["details"]
                            )
                        elif isinstance(block["details"], dict):
                            block["details"] = json.dumps(block["details"])
                        logger.debug(
                            f"Transformed details for block {block['content_block']}: {block['details']}"
                        )

                transformed_response = GenerateDraftResponse.model_validate_json(
                    json.dumps(json_data)
                )
                logger.info(
                    f"Successfully parsed response into GenerateDraftResponse model for {request_type}"
                )
                return transformed_response
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                raise
            except Exception as e:
                logger.error(f"Error parsing JSON response: {e}")
                raise
        # Add more parsing logic for other request types as needed
        raise ValueError(f"Unsupported request type: {request_type}")
