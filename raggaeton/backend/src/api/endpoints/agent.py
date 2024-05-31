import os
import logging
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.agent import ReActAgent
from llama_index.core import Settings
from raggaeton.backend.src.utils.common import load_config, base_dir
from raggaeton.backend.src.utils.common import config_loader

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_custom_prompt() -> str:
    prompt_path = os.path.join(base_dir, "raggaeton/backend/src/config", "prompts.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as file:
            return file.read()
    return ""


def init_llm(model_name, params, api_key_env):
    logger.debug(
        f"Initializing LLM with model_name: {model_name}, params: {params}, api_key_env: {api_key_env}"
    )

    if "openai" in model_name.lower() or model_name.lower() == "gpt-4o":
        from llama_index.llms.openai import OpenAI

        Settings.llm = OpenAI(model=model_name, **params)
    elif "anthropic" in model_name.lower():
        from llama_index.llms.anthropic import Anthropic

        Settings.llm = Anthropic(model=model_name, **params)
    else:
        raise ValueError(f"Unsupported LLM: {model_name}")

    os.environ[api_key_env] = config_loader.get_secret(api_key_env)


def create_agent(
    agent_type,
    tools,
    config=None,
    model_name=None,
    params=None,
    api_key_env=None,
    verbose=False,
):
    """
    Create an agent with the specified type and tools.

    Args:
        agent_type (str): The type of agent to create (e.g., "openai", "react").
        tools (list): List of tools to be used by the agent.
        config (dict, optional): Configuration dictionary. If not provided, load the default config.
        model_name (str, optional): The name of the model to initialize. Overrides config if provided.
        params (dict, optional): Parameters for the model. Overrides config if provided.
        api_key_env (str, optional): The environment variable for the API key. Overrides config if provided.
        verbose (bool, optional): Whether to enable verbose logging. Default is False.

    Returns:
        Agent: The created agent.
    """
    if config is None:
        config = load_config()

    # Extract model configuration from the config if not provided
    if model_name is None or params is None or api_key_env is None:
        llm_config = config["llm"]["models"][0]
        model_name = model_name or llm_config["model_name"]
        params = params or llm_config["params"]
        api_key_env = api_key_env or llm_config["api_key_env"]

    logger.debug(
        f"Initializing LLM with model_name: {model_name}, params: {params}, api_key_env: {api_key_env}"
    )
    init_llm(model_name, params, api_key_env)
    custom_prompt = get_custom_prompt()

    if agent_type == "openai":
        return OpenAIAgent.from_tools(
            tools, system_prompt=custom_prompt, verbose=verbose
        )
    elif agent_type == "react":
        return ReActAgent.from_tools(
            tools, system_prompt=custom_prompt, verbose=verbose
        )
    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")
