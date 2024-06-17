import yaml
import os
import json
from raggaeton.backend.src.utils.common import find_project_root, logger
from raggaeton.backend.src.utils.error_handler import error_handling_context

base_dir = find_project_root(os.path.dirname(__file__))
config_path = os.path.join(
    base_dir, "raggaeton", "backend", "src", "config", "config.yaml"
)
prompts_dir = os.path.join(base_dir, "raggaeton", "backend", "src", "config", "prompts")
content_blocks_path = os.path.join(
    base_dir,
    "raggaeton",
    "backend",
    "src",
    "config",
    "article_templates",
    "content_blocks.json",
)


def load_yaml(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def load_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


config = load_yaml(config_path)
content_blocks = load_json(content_blocks_path)

prompts = {}
for file_name in os.listdir(prompts_dir):
    if file_name.endswith(".yaml"):
        file_path = os.path.join(prompts_dir, file_name)
        loaded_prompts = load_yaml(file_path)
        prompts.update(loaded_prompts)


def get_content_block_suggestions(structures):
    suggestions = []
    unique_blocks = set()
    for structure in structures:
        for block in structure:
            if block in content_blocks and block not in unique_blocks:
                unique_blocks.add(block)
                block_details = content_blocks[block]["details"]
                required_details = ", ".join(block_details["required"])
                optional_details = ", ".join(block_details.get("optional", []))
                suggestions.append(
                    {
                        "content_block": block,
                        "description": content_blocks[block]["description"],
                        "required": required_details,
                        "optional": optional_details,
                    }
                )
    return suggestions


def get_optional_params(params, **kwargs):
    # Ensure 'optional_params' is included in params
    if "optional_params" not in params:
        params["optional_params"] = {}

    # Ensure 'personas' and other optional keys are included in 'optional_params'
    optional_keys = [
        "data",
        "publication",
        "country",
        "personas",
        "desired_length",
        "scratchpad",
        "include_token_count",
        "limit",
    ]
    for key in optional_keys:
        if key not in params["optional_params"]:
            params["optional_params"][key] = None
            # params["optional_params"][key] = ""

    # Include additional keyword arguments
    params.update(kwargs)
    return {k: v for k, v in params.items() if v is not None}


def get_prompts(function_name, request, **kwargs):
    logger.info(f"Get Prompts - Received request {request} with kwargs: {kwargs}")

    system_prompt = prompts[function_name].get("system_prompt", "")

    # Convert the request model to a dictionary, excluding unset and None values
    params = request.model_dump(exclude_unset=True, exclude_none=True)

    # Get optional parameters
    params = get_optional_params(params, **kwargs)
    logger.debug(f"Formatted parameters for prompt: {params}")

    # Fetch content block suggestions based on the structures defined in the YAML file
    structures = prompts[function_name].get("structures", [])
    content_block_suggestions = (
        get_content_block_suggestions(structures) if structures else []
    )

    with error_handling_context():
        message_prompt = prompts[function_name]["message_prompt"].format(**params)

    # Include content block suggestions in the prompt if available
    if content_block_suggestions:
        message_prompt += "\n\nContent Block Suggestions:\n"
        for suggestion in content_block_suggestions:
            message_prompt += (
                f"- **{suggestion['content_block']}**: {suggestion['description']}\n"
            )
            message_prompt += f"  - Required: {suggestion['required']}\n"
            if suggestion["optional"]:
                message_prompt += f"  - Optional: {suggestion['optional']}\n"

    logger.debug(f"Formatted message prompt: {message_prompt}")

    return system_prompt, message_prompt
