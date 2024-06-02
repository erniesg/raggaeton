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

logger = logging.getLogger(__name__)
agent = None


def get_custom_prompt() -> str:
    prompt_path = os.path.join(base_dir, "raggaeton/backend/src/config", "prompts.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as file:
            prompt = file.read()
            # Replace placeholder with the actual date
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
        raise ValueError(f"Unsupported LLM: {model_name}")

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
    global agent

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
        agent = OpenAIAgent.from_tools(
            tools, system_prompt=custom_prompt, verbose=verbose
        )
    elif agent_type == "react":
        agent = ReActAgent.from_tools(
            tools, system_prompt=custom_prompt, verbose=verbose
        )
    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")
    logger.debug(f"Agent created with custom prompt: {custom_prompt}")

    return agent


def init_agent(index_path=None):
    global agent
    if agent is None:
        logger.info("Initializing agent components...")
        config = load_config()

        google_search_tool = create_google_search_tool()

        # Use the default index path if none is provided
        if index_path is None:
            index_path = os.path.join(base_dir, ".ragatouille/colbert/indexes/my_index")

        logger.debug(f"Using index path: {index_path}")

        # Check if the index path exists
        if os.path.exists(index_path):
            # Load the RAG query tool with the existing index
            rag_query_tool = load_rag_query_tool(index_path=index_path)
            tools = [google_search_tool, rag_query_tool]
        else:
            logger.warning(
                f"Index path {index_path} does not exist. Initializing agent with default configuration."
            )
            documents = load_documents()
            tools = [google_search_tool, create_rag_query_tool(docs=documents)]

        # Initialize the agent with pre-loaded tools
        agent = create_agent(
            agent_type="openai",
            tools=tools,
            config=config,
        )
        logger.info(f"Agent initialized successfully with type: {type(agent)}")
    else:
        logger.info("Agent is already initialized")
    return agent


def load_agent(index_path=None):
    global agent
    if agent is None:
        logger.info("Loading agent components...")
        config = load_config()

        google_search_tool = create_google_search_tool()

        if index_path is None:
            # Use the default index path
            index_path = os.path.join(base_dir, ".ragatouille/colbert/indexes/my_index")

        logger.debug(f"Using index path: {index_path}")

        # Check if the index path exists
        if not os.path.exists(index_path):
            logger.warning(
                f"Index path {index_path} does not exist. Initializing agent with default configuration."
            )
            return init_agent()

        # Create the RAG query tool with the loaded index
        rag_query_tool = load_rag_query_tool(index_path=index_path)

        # Initialize the agent with pre-loaded tools
        agent = create_agent(
            agent_type="openai",
            tools=[google_search_tool, rag_query_tool],
            config=config,
        )
        logger.info(f"Agent loaded successfully with type: {type(agent)}")
    else:
        logger.info("Agent is already loaded")
    return agent
