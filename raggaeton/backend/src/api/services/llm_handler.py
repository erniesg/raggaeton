import os
from tiktoken import get_encoding
from raggaeton.backend.src.api.services.prompts import get_prompts, config
import anthropic
import openai
from raggaeton.backend.src.utils.error_handler import error_handling_context, LLMError
from raggaeton.backend.src.utils.llm_processing import parse_llm_response
from langfuse.decorators import observe, langfuse_context
import logging

logger = logging.getLogger(__name__)

enc = get_encoding("cl100k_base")


def count_tokens(text):
    return len(enc.encode(text))


class LLMHandler:
    def __init__(self, api_key=None, provider=None, model_name=None, session_id=None):
        self.provider = provider or config["llm"].get("default_provider")
        self.model_name = model_name or config["llm"]["default_model"]
        self.session_id = session_id
        logger.info(
            f"Initializing LLMHandler with provider: {self.provider}, model: {self.model_name}, session_id: {self.session_id}"
        )

        if self.provider == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=api_key or os.getenv("CLAUDE_API_KEY")
            )
        elif self.provider == "openai":
            self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError("Unsupported provider")

    @observe(as_type="generation")
    def call_llm(self, function_name, request, model_name=None, **kwargs):
        logger.debug(f"LLM Handler - Received kwargs in call_llm: {kwargs}")
        # Ensure edit_type is included in kwargs if present in request
        if hasattr(request, "edit_type"):
            kwargs["edit_type"] = request.edit_type

        system_prompt, message_prompt = get_prompts(function_name, request, **kwargs)
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"Message Prompt: {message_prompt}")

        # Use the default model from the config if model_name is not provided
        model_to_use = model_name if model_name else self.model_name
        logger.info(f"Using model: {model_to_use}")

        # Enrich the trace with input, model, and metadata
        langfuse_context.update_current_observation(
            name=f"llm_handler_{function_name}",
            input={"system_prompt": system_prompt, "message_prompt": message_prompt},
            model=model_to_use,
            metadata=kwargs,
        )

        # Update the trace with the session ID
        langfuse_context.update_current_trace(session_id=self.session_id)

        with error_handling_context():
            if self.provider == "anthropic":
                with self.client.messages.stream(
                    model=model_to_use,
                    max_tokens=4096,
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
            logger.debug(f"Full response content: {full_content}")

            # Enrich the trace with output
            langfuse_context.update_current_observation(
                output=full_content,
                metadata={
                    "token_count": token_count,
                    "model_name": model_to_use,
                    "kwargs": kwargs,
                },
            )

            # Parse the response into the appropriate Pydantic model
            logger.debug(
                f"Calling parse_llm_response with function_name: {function_name}"
            )

            try:
                parsed_response = parse_llm_response(
                    full_content,
                    function_name,
                    request_data=request.model_dump() if request else {},
                )
                logger.debug("Successfully called parse_llm_response")
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {e}")
                raise LLMError(f"Failed to parse LLM response: {e}")

            return parsed_response, token_count
