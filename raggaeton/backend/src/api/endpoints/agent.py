import os
import logging
from datetime import datetime
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.agent import ReActAgent
from llama_index.core import Settings
from raggaeton.backend.src.utils.common import load_config, base_dir, config_loader
from raggaeton.backend.src.api.endpoints.tools import (
    create_google_search_tool,
    create_rag_query_tool,
)
from raggaeton.backend.src.api.endpoints.index import load_documents
from raggaeton.backend.src.api.endpoints.tools import load_rag_query_tool
from raggaeton.backend.src.utils.error_handler import ConfigurationError
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
agent = None
cached_agents: Dict[str, Any] = {}


def get_custom_prompt() -> str:
    prompt_path = os.path.join(base_dir, "raggaeton/backend/src/config", "prompts.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as file:
            prompt = file.read()
            today_date = datetime.now().strftime("%Y-%m-%d")
            prompt = prompt.replace("{insert today's date here}", today_date)
            logger.debug(f"Custom prompt loaded: {prompt}")
            return prompt
    logger.warning(f"Custom prompt file not found at: {prompt_path}")
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
        raise ConfigurationError(f"Unsupported LLM: {model_name}")

    os.environ[api_key_env] = config_loader.get_secret(api_key_env)


def create_agent(
    agent_type,
    tools,
    config=None,
    model_name=None,
    params=None,
    api_key_env=None,
    verbose=True,
):
    global agent

    if config is None:
        config = load_config()

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
        agent = OpenAIAgent.from_tools(
            tools, system_prompt=custom_prompt, verbose=verbose
        )
    elif agent_type == "react":
        agent = ReActAgent.from_tools(
            tools, system_prompt=custom_prompt, verbose=verbose
        )
    else:
        raise ConfigurationError(f"Unsupported agent type: {agent_type}")
    logger.debug(f"Agent created with custom prompt: {custom_prompt}")

    return agent


def init_agent(index_path=None, **kwargs):
    logger.debug("init_agent called")

    global agent

    # Check if an agent with the given configuration exists in the cache
    cached_agent = check_agent_state(index_path, **kwargs)
    if cached_agent:
        logger.info("Using cached agent")
        return cached_agent

    logger.info("Initializing agent components...")
    config = load_config()
    logger.debug(f"Loaded config: {config}")

    google_search_tool = create_google_search_tool()
    logger.debug("Created Google search tool")

    if index_path is None:
        index_path = os.path.join(base_dir, ".ragatouille/colbert/indexes/my_index")

    logger.debug(f"Using index path: {index_path}")

    if os.path.exists(index_path):
        logger.debug(f"Index path {index_path} exists. Loading RAG query tool.")
        rag_query_tool = load_rag_query_tool(index_path=index_path)
        tools = [google_search_tool, rag_query_tool]
    else:
        logger.warning(
            f"Index path {index_path} does not exist. Initializing agent with default configuration."
        )
        documents = load_documents()
        logger.debug(f"Loaded documents: {documents}")
        tools = [google_search_tool, create_rag_query_tool(docs=documents)]

    agent = create_agent(agent_type="openai", tools=tools, config=config)
    logger.info(f"Agent initialized successfully with type: {type(agent)}")

    # Store the initialized agent in the cache
    cached_agents[f"{index_path}_{kwargs}"] = agent

    return agent


def check_agent_state(index_path: str, **kwargs) -> Optional[Any]:
    config_key = f"{index_path}_{kwargs}"

    if config_key in cached_agents:
        logger.info(f"Found cached agent for configuration: {config_key}")
        return cached_agents[config_key]
    else:
        logger.info(f"No cached agent found for configuration: {config_key}")
        return None


def get_agent(index_path=None, **kwargs):
    logger.debug("get_agent called")

    # Check if an agent with the given configuration exists in the cache
    cached_agent = check_agent_state(index_path, **kwargs)
    if cached_agent:
        logger.info("Using cached agent")
        return cached_agent

    # Initialize a new agent if not found in the cache
    agent = init_agent(index_path, **kwargs)

    # Store the initialized agent in the cache
    config_key = f"{index_path}_{kwargs}"
    cached_agents[config_key] = agent

    logger.info(f"Agent initialized and cached with configuration: {config_key}")
    return agent
