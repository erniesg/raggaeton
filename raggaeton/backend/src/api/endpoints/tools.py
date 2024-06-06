import logging
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine
from llama_index.core.selectors.llm_selectors import LLMSingleSelector
from llama_index.packs.ragatouille_retriever.base import RAGatouilleRetrieverPack
from llama_index.tools.google import GoogleSearchToolSpec
from llama_index.llms.openai import OpenAI
from raggaeton.backend.src.utils.gcs import save_data, create_bucket
from raggaeton.backend.src.utils.common import config_loader, base_dir
from raggaeton.backend.src.utils.utils import create_mock_document, create_indices
from raggaeton.backend.src.utils.error_handler import DataError, ConfigurationError

import os

config_loader._setup_logging()
logger = logging.getLogger(__name__)


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
    docs, index_name="my_index", model_name="gpt-4o", top_k=10, index_path=None
):
    pack_path = os.path.join(base_dir, "raggaeton/backend/src/config/ragatouille_pack")
    logger.info(f"Ragatouille pack at: {pack_path}")

    if index_path:
        logger.info(f"Index path provided: {index_path}")
        if not os.path.exists(index_path):
            raise DataError(f"Index path {index_path} does not exist")
        logger.info(f"Loading RAGatouilleRetrieverPack from {index_path}")
        ragatouille_pack = RAGatouilleRetrieverPack(
            docs,
            llm=OpenAI(model=model_name),
            index_name=index_name,
            top_k=top_k,
            index_path=index_path,
        )
    else:
        logger.info("No index path provided, creating new RAGatouilleRetrieverPack")
        ragatouille_pack = RAGatouilleRetrieverPack(
            docs, llm=OpenAI(model=model_name), index_name=index_name, top_k=top_k
        )
        logger.info("Saving index data to GCS...")
        bucket_name = config_loader.get_config().get("gcs", {}).get("bucket_name")
        create_bucket(bucket_name)
        save_data(local_path=os.path.join(base_dir, ".ragatouille/colbert/indexes"))
        logger.info("Index data saved to GCS successfully.")

    rag_query = ragatouille_pack.get_modules()["query_engine"]
    logger.info(f"Ragatouille indexed at: {ragatouille_pack.index_path}")

    return QueryEngineTool.from_defaults(
        query_engine=rag_query,
        name="colbert_query_tool",
        description="COLBert tool for retrieval from selected sample of 900 Tech in Asia posts",
    )


def create_tools(*tool_names, **kwargs):
    tools = []
    for tool_name in tool_names:
        if tool_name == "vector":
            vector_index = kwargs.get("vector_index")
            if vector_index:
                tools.append(create_vector_tool(vector_index))
            else:
                raise ConfigurationError(
                    "vector_index is required for creating vector tool"
                )
        elif tool_name == "summary":
            summary_index = kwargs.get("summary_index")
            if summary_index:
                tools.append(create_summary_tool(summary_index))
            else:
                raise ConfigurationError(
                    "summary_index is required for creating summary tool"
                )
        elif tool_name == "search":
            tools.append(create_google_search_tool())
        elif tool_name == "rag":
            docs = kwargs.get("docs")
            if docs:
                tools.append(create_rag_query_tool(docs))
            else:
                raise ConfigurationError(
                    "docs are required for creating RAG query tool"
                )
        else:
            raise ConfigurationError(f"Unsupported tool name: {tool_name}")
    return tools


def create_router_query_engine(vector_store, documents):
    vector_index, summary_index = create_indices(vector_store, documents)
    summary_tool, vector_tool, google_search_tool = create_tools(
        "summary",
        "vector",
        "search",
        vector_index=vector_index,
        summary_index=summary_index,
    )

    router_query_engine = RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(),
        query_engine_tools=[summary_tool, vector_tool, google_search_tool],
        verbose=True,
    )
    logger.info("Router query engine created")

    return router_query_engine, vector_index, summary_index


def load_rag_query_tool(index_path=None, docs=None):
    if docs is None:
        logger.debug("No documents are passed in, using a mock document")
        docs = [create_mock_document()]

    if index_path is None:
        index_path = os.path.join(
            base_dir, "raggaeton/raggaeton/.ragatouille/colbert/indexes/my_index"
        )

    logger.debug(f"Loading RAG query tool from index path: {index_path}")

    return create_rag_query_tool(docs, index_path=index_path)
