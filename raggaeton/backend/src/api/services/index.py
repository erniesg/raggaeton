import os
from raggaeton.backend.src.utils.common import logger, base_dir, config_loader
from llama_index.packs.ragatouille_retriever.base import RAGatouilleRetrieverPack
from llama_index.llms.openai import OpenAI
from raggaeton.backend.src.api.endpoints.tools import load_rag_query_tool
from raggaeton.backend.src.utils.error_handler import DataError

config = config_loader.get_config()
INDEX_PATH = os.path.join(
    base_dir, ".ragatouille/colbert/indexes", config["index_name"]
)


def create_ragatouille_index(docs, index_name):
    if os.path.exists(INDEX_PATH):
        try:
            ragatouille_pack = load_rag_query_tool(index_path=INDEX_PATH, docs=docs)
        except DataError as e:
            logger.error(f"Failed to load existing index: {e}")
            raise
    else:
        ragatouille_pack = RAGatouilleRetrieverPack(
            documents=docs,
            llm=OpenAI(model="gpt-4o"),
            index_name=index_name,
            top_k=10,
        )
    return ragatouille_pack


def retrieve_nodes(ragatouille_pack, query):
    retriever = ragatouille_pack.get_modules()["retriever"]
    nodes = retriever.retrieve(query)
    return nodes


def construct_query(topic, keywords):
    return f"Research on {topic} with keywords: {', '.join(keywords)}"
