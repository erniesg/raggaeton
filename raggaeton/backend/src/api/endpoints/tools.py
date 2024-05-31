import logging
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine
from llama_index.core.selectors.llm_selectors import LLMSingleSelector
from llama_index.tools.google import GoogleSearchToolSpec
from llama_index.packs.ragatouille_retriever import RAGatouilleRetrieverPack
from llama_index.llms.openai import OpenAI
from raggaeton.backend.src.utils.utils import create_indices  # Updated import
from raggaeton.backend.src.utils.common import config_loader  # Import the config_loader

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_vector_tool(vector_index):
    vector_query_engine = vector_index.as_query_engine()
    return QueryEngineTool.from_defaults(
        query_engine=vector_query_engine,
        description="Useful for retrieving specific context from the documents.",
    )


def create_summary_tool(summary_index):
    summary_query_engine = summary_index.as_query_engine()
    return QueryEngineTool.from_defaults(
        query_engine=summary_query_engine,
        description="Useful for summarization questions related to the documents.",
    )


def create_google_search_tool():
    google_search_tool_spec = GoogleSearchToolSpec(
        key=config_loader.get_secret("GOOGLE_API_KEY"),
        engine=config_loader.get_secret("GOOGLE_SEARCH_ENGINE_ID"),
        num=3,
    )
    logger.info("Google search tool created")
    google_search_tools = google_search_tool_spec.to_tool_list()
    return google_search_tools[0]  # Extract the first tool


def create_rag_query_tool(
    docs, index_name="my_index", model_name="gpt-3.5-turbo", top_k=10
):
    ragatouille_pack = RAGatouilleRetrieverPack(
        docs, llm=OpenAI(model=model_name), index_name=index_name, top_k=top_k
    )
    rag_query = ragatouille_pack.get_modules()["query_engine"]
    return QueryEngineTool.from_defaults(
        query_engine=rag_query, name="colbert_query_tool", description="RAGGA tool"
    )


def create_tools(*tool_names, **kwargs):
    """
    Create a list of tools based on the provided tool names.

    Args:
        *tool_names (str): Names of the tools to create.
        **kwargs: Additional arguments required for tool creation.

    Returns:
        list: List of created tools.

    Usage:
        tools = create_tools("search", "rag", docs=docs)
    """
    tools = []
    for tool_name in tool_names:
        if tool_name == "vector":
            vector_index = kwargs.get("vector_index")
            if vector_index:
                tools.append(create_vector_tool(vector_index))
            else:
                raise ValueError("vector_index is required for creating vector tool")
        elif tool_name == "summary":
            summary_index = kwargs.get("summary_index")
            if summary_index:
                tools.append(create_summary_tool(summary_index))
            else:
                raise ValueError("summary_index is required for creating summary tool")
        elif tool_name == "search":
            tools.append(create_google_search_tool())
        elif tool_name == "rag":
            docs = kwargs.get("docs")
            if docs:
                tools.append(create_rag_query_tool(docs))
            else:
                raise ValueError("docs are required for creating RAG query tool")
        else:
            raise ValueError(f"Unsupported tool name: {tool_name}")
    return tools


def create_router_query_engine(vector_store, documents):
    """
    Create a Router Query Engine.

    Args:
        vector_store: The vector store to use.
        documents: The documents to use.

    Returns:
        tuple: The created Router Query Engine, vector index, and summary index.

    Usage:
        router_query_engine, vector_index, summary_index = create_router_query_engine(vector_store, documents)
    """
    vector_index, summary_index = create_indices(vector_store, documents)
    summary_tool, vector_tool, google_search_tool = create_tools(
        vector_index, summary_index
    )

    router_query_engine = RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(),
        query_engine_tools=[summary_tool, vector_tool, google_search_tool],
        verbose=True,
    )
    logger.info("Router query engine created")

    return router_query_engine, vector_index, summary_index