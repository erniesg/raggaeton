import yaml
import os
from raggaeton.backend.src.utils.common import find_project_root, logger
from raggaeton.backend.src.utils.error_handler import error_handling_context

base_dir = find_project_root(os.path.dirname(__file__))
config_path = os.path.join(
    base_dir, "raggaeton", "backend", "src", "config", "config.yaml"
)
prompts_dir = os.path.join(base_dir, "raggaeton", "backend", "src", "config", "prompts")


def load_yaml(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


config = load_yaml(config_path)

prompts = {}
for file_name in os.listdir(prompts_dir):
    if file_name.endswith(".yaml"):
        file_path = os.path.join(prompts_dir, file_name)
        loaded_prompts = load_yaml(file_path)
        prompts.update(loaded_prompts)


def get_prompts(function_name, request, **kwargs):
    logger.info(f"Get Prompts - Received request {request} with kwargs: {kwargs}")

    system_prompt = prompts[function_name].get("system_prompt", "")

    # Convert the request model to a dictionary, excluding unset and None values
    params = request.model_dump(exclude_unset=True, exclude_none=True)

    # Ensure 'optional_params' is included in params
    if "optional_params" not in params:
        params["optional_params"] = {}

    # Ensure 'personas' and other optional keys are included in 'optional_params'
    optional_keys = [
        "personas",
        "country",
        "desired_length",
        "scratchpad",
        "include_token_count",
        "limit",
    ]
    for key in optional_keys:
        if key not in params["optional_params"]:
            params["optional_params"][key] = None

    # Include additional keyword arguments
    params.update(kwargs)
    params = {k: v for k, v in params.items() if v is not None}
    logger.debug(f"Formatted parameters for prompt: {params}")

    with error_handling_context():
        message_prompt = prompts[function_name]["message_prompt"].format(**params)

    logger.debug(f"Formatted parameters for prompt: {params}")

    return system_prompt, message_prompt
