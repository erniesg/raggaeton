import os
from tiktoken import get_encoding
from raggaeton.backend.src.api.services.prompts import get_prompts, config
import anthropic
import openai
from raggaeton.backend.src.utils.common import logger
from raggaeton.backend.src.utils.error_handler import error_handling_context, LLMError
from raggaeton.backend.src.utils.llm_processing import parse_llm_response


enc = get_encoding("cl100k_base")


def count_tokens(text):
    return len(enc.encode(text))


class LLMHandler:
    def __init__(self, api_key=None, provider="openai"):
        self.provider = provider
        if provider == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
            )
        elif provider == "openai":
            self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError("Unsupported provider")

    def call_llm(self, function_name, request, model_name=None, **kwargs):
        logger.info(f"LLM Handler - Received kwargs in call_llm: {kwargs}")
        # Ensure edit_type is included in kwargs if present in request
        if hasattr(request, "edit_type"):
            kwargs["edit_type"] = request.edit_type

        system_prompt, message_prompt = get_prompts(function_name, request, **kwargs)
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"Message Prompt: {message_prompt}")

        # Use the default model from the config if model_name is not provided
        model_to_use = model_name if model_name else config["llm"]["default_model"]

        with error_handling_context():
            if self.provider == "anthropic":
                with self.client.messages.stream(
                    model=model_to_use,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": message_prompt}],
                    system=system_prompt if system_prompt else None,
                ) as stream:
                    content = []
                    for text in stream.text_stream:
                        content.append(text)
                full_content = "".join(content)
            elif self.provider == "openai":
                stream = self.client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message_prompt},
                    ],
                    stream=True,
                    response_format={"type": "json_object"},
                )

                content = []
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        chunk_message = chunk.choices[0].delta.content
                        content.append(chunk_message)
                full_content = "".join(content)
            else:
                raise ValueError("Unsupported provider")

            token_count = count_tokens(full_content)
            logger.info(
                f"LLM API request completed with response: {(full_content[:500] + '...') if len(full_content) > 500 else full_content}"
                f"\nResponse type: {type(full_content)}"
                f"\nToken count: {token_count}"
            )
            logger.info(f"Full response content: {full_content}")

            # Parse the response into the appropriate Pydantic model
            logger.info(
                f"Calling parse_llm_response with function_name: {function_name}"
            )

            try:
                parsed_response = parse_llm_response(
                    full_content,
                    function_name,
                    request_data=request.model_dump() if request else {},
                )
                logger.info("Successfully called parse_llm_response")
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {e}")
                raise LLMError(f"Failed to parse LLM response: {e}")

            return parsed_response, token_count
