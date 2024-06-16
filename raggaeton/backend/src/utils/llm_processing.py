from pydantic import BaseModel, ValidationError
from raggaeton.backend.src.schemas.research import GenerateResearchQuestionsResponse
from raggaeton.backend.src.utils.common import logger
from raggaeton.backend.src.utils.error_handler import error_handling_context
import json


def parse_llm_response(response_content: str, request_type: str) -> BaseModel:
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
                # Directly parse the JSON string into a Pydantic model instance using model_validate_json
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
        # Add more parsing logic for other request types as needed
        raise ValueError(f"Unsupported request type: {request_type}")
