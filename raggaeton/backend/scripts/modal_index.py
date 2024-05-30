import os
import logging
import modal
import psycopg2
from typing import List, Dict, Any
from llama_index.core import SummaryIndex, VectorStoreIndex, Settings
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.selectors.llm_selectors import LLMSingleSelector
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Define the Modal image with necessary dependencies
index_image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "requests",
    "supabase",
    "PyYAML",
    "python-dotenv",
    "llama-index",
    "llama-index-readers-database",
    "llama-index-embeddings-huggingface",
    "llama-index-vector-stores-supabase",
    "llama-index-callbacks-deepeval",
    "psycopg2-binary",
    "deepeval",
    "llama-index-tools-google",
    "llama-index-callbacks-arize-phoenix",
    "arize-phoenix[evals]",
)

# Define the Modal app
app = modal.App(name="raggaeton-index-app", image=index_image)

index_volume = modal.Volume.from_name("index-storage", create_if_missing=True)

# Mount the local directory
raggaeton_mount = modal.Mount.from_local_dir(
    local_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
    remote_path="/app/raggaeton",
    condition=lambda pth: not pth.endswith(".env")
    and not pth.endswith("modal_index.py"),
    recursive=True,
)


@app.local_entrypoint()
def main():
    logger.info("Starting main function")
    index_name = "my_index"
    embedding_model = "Alibaba-NLP/gte-base-en-v1.5"
    chunk_size = 512
    overlap = 128
    dimension = 768
    limit = 10
    logger.info("Calling create_index function with parameters")
    create_index.remote(
        index_name, embedding_model, chunk_size, overlap, dimension, limit
    )


@app.function(
    mounts=[raggaeton_mount],
    volumes={"/cache": index_volume},
    secrets=[
        modal.Secret.from_name("my-postgres-secret"),
        modal.Secret.from_name("my-openai-secret"),
        modal.Secret.from_name("my-search-secret"),
    ],
    gpu="any",
    _allow_background_volume_commits=True,
)
def create_index(
    index_name, embedding_model, chunk_size, overlap, dimension, limit, config=None
):
    logger.info("Starting create_index function")
    import sys

    sys.path.insert(0, "/app/raggaeton")

    from raggaeton.backend.src.utils.common import load_config
    from raggaeton.backend.src.utils.utils import convert_to_documents

    os.getenv("OPENAI_API_KEY")

    # Set the cache directory for transformers
    os.environ["TRANSFORMERS_CACHE"] = "/cache"

    # Use config defaults if parameters are not provided
    if config is None:
        config = load_config()

    logger.info(f"Index name: {index_name}")
    logger.info(f"Embedding model: {embedding_model}")
    logger.info(f"Chunk size: {chunk_size}")
    logger.info(f"Overlap: {overlap}")
    logger.info(f"Dimension: {dimension}")

    index = index_name or config["index_name"]
    embedding_model = embedding_model or config["embedding"]["models"][0]
    chunk_size = chunk_size or config["document"]["chunk_size"][0]
    overlap = overlap or config["document"]["overlap"][0]
    dimension = dimension or config["embedding"]["dimension"][0]

    # Set the chunk size and overlap in the Settings object
    Settings.chunk_size = chunk_size
    Settings.chunk_overlap = overlap

    # Load data from PostgreSQL with a limit
    db_params = {
        "host": os.getenv("PGHOST"),
        "port": os.getenv("PGPORT"),
        "user": os.getenv("PGUSER"),
        "password": os.getenv("PGPASSWORD"),
        "dbname": os.getenv("PGDATABASE"),
    }
    rows = load_data_from_postgres(db_params, config["table_posts"], limit)

    # Convert rows to Document objects
    documents = convert_to_documents(rows)

    # Log the retrieved documents
    logger.info(f"Retrieved {len(documents)} documents from the database.")
    logger.info(
        f"Document sample: {documents[0] if documents else 'No documents retrieved'}"
    )

    # Create the embedding model with trust_remote_code=True
    embed_model = HuggingFaceEmbedding(
        model_name=embedding_model, trust_remote_code=True
    )
    Settings.embed_model = embed_model

    # Create the vector store
    vector_store = SupabaseVectorStore(
        postgres_connection_string=f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}",
        collection_name=index,
        dimension=dimension,
    )
    logger.info("Vector store created")

    # Create the pipeline with transformations
    pipeline = IngestionPipeline(
        transformations=[MarkdownNodeParser(), embed_model],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
    )
    logger.info("Pipeline created")

    # Process documents
    pipeline.run(documents=documents)

    logger.info("Documents processed and summary index created")

    # # Create the index from the vector store
    # index = VectorStoreIndex.from_vector_store(vector_store)
    # logger.info("Index created from vector store")

    router_query_engine, vector_index = create_router_query_engine(
        vector_store, documents
    )

    # Save the index to a Modal volume
    # persist_dir = "/cache/index"
    # vector_query_engine.storage_context.persist(persist_dir=persist_dir)
    # logger.info(f"Index saved with ID: {index_name}")

    # Create the chat engine with the router query engine
    chat_engine = vector_index.as_chat_engine(
        chat_mode="best", verbose=True, query_engine=router_query_engine
    )

    # chat_engine = index.as_chat_engine(chat_mode="best", verbose=True)

    # query_engine = index.as_query_engine()
    # response = chat_engine.query("What's up recently?")
    response = chat_engine.chat("Why are Asian sports stars getting into VC space?")
    logger.info(f"Response: {response}")

    response = chat_engine.chat("Tell me about Grab’s profitability.")
    logger.info(f"Response: {response}")

    response = chat_engine.chat("Which 10 startups out of Africa are most promising?")
    logger.info(f"Response: {response}")

    return {"status": "Index created and evaluated successfully"}


def load_data_from_postgres(
    db_params: Dict[str, str], table_name: str, limit: int
) -> List[Dict[str, Any]]:
    conn = psycopg2.connect(
        host=db_params["host"],
        port=db_params["port"],
        user=db_params["user"],
        password=db_params["password"],
        dbname=db_params["dbname"],
    )
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert rows to a list of dictionaries
    data = [dict(zip(columns, row)) for row in rows]
    return data


def create_router_query_engine(vector_store, documents):
    # Create the vector index
    vector_index = VectorStoreIndex.from_vector_store(vector_store)
    logger.info("Vector index created from vector store")

    # Create the summary index
    summary_index = SummaryIndex.from_documents(documents)
    logger.info("Summary index created from documents")

    # Create query engines
    vector_query_engine = vector_index.as_query_engine()
    summary_query_engine = summary_index.as_query_engine()

    # Create tools
    summary_tool = QueryEngineTool.from_defaults(
        query_engine=summary_query_engine,
        description="Useful for summarization questions related to the documents.",
    )

    vector_tool = QueryEngineTool.from_defaults(
        query_engine=vector_query_engine,
        description="Useful for retrieving specific context from the documents.",
    )

    # google_search_tool_spec = GoogleSearchToolSpec(
    #     key=os.getenv("GOOGLE_API_KEY"),
    #     engine=os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
    #     num=5,
    # )
    # logger.info("Google search tool created")

    # google_search_tools = LoadAndSearchToolSpec.from_defaults(
    #     google_search_tool_spec.to_tool_list()[0]
    # ).to_tool_list()
    # google_search_tool = google_search_tools[1]  # Extract the search tool

    # Create Router Query Engine
    router_query_engine = RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(),
        query_engine_tools=[summary_tool, vector_tool],
        verbose=True,
    )
    logger.info("Router query engine created")

    return router_query_engine, vector_index
