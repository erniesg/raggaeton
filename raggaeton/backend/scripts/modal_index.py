import os
import logging
import modal
import psycopg2
from typing import List, Dict, Any
from datetime import datetime

from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.node_parser import MarkdownNodeParser
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
    "psycopg2-binary",
)

# Define the Modal app
app = modal.App(
    name="raggaeton-index-app",
    image=index_image,
    secrets=[modal.Secret.from_name("my-postgres-secret")],
)

# Mount the local directory
raggaeton_mount = modal.Mount.from_local_dir(
    local_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
    remote_path="/app/raggaeton",
    condition=lambda pth: not pth.endswith(".env")
    and not pth.endswith("modal_index.py"),
    recursive=True,
)

# Define a volume for caching the embedding model
embedding_volume = modal.Volume.from_name("embedding-cache", create_if_missing=True)


@app.local_entrypoint()
def main():
    index_name = "my_index"
    embedding_model = "Alibaba-NLP/gte-base-en-v1.5"
    chunk_size = 512
    overlap = 128
    dimension = 768
    limit = 10

    # Call the Modal function
    create_index.remote(
        index_name, embedding_model, chunk_size, overlap, dimension, limit
    )


@app.function(
    mounts=[raggaeton_mount],
    volumes={"/cache": embedding_volume},
    secrets=[
        modal.Secret.from_name("my-postgres-secret"),
        modal.Secret.from_name("my-openai-secret"),
    ],
    gpu="any",
)
def create_index(
    index_name, embedding_model, chunk_size, overlap, dimension, limit, config=None
):
    import sys

    sys.path.insert(0, "/app/raggaeton")

    from raggaeton.backend.src.utils.common import load_config

    os.getenv("OPENAI_API_KEY")

    # Set the cache directory for transformers
    os.environ["TRANSFORMERS_CACHE"] = "/cache"

    # Use config defaults if parameters are not provided
    if config is None:
        config = load_config()

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
        collection_name=index_name,
        dimension=dimension,
    )

    # Create the pipeline with transformations
    pipeline = IngestionPipeline(
        transformations=[MarkdownNodeParser(), embed_model],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
    )

    # Process documents
    pipeline.run(documents=documents)

    index = VectorStoreIndex.from_vector_store(vector_store)

    # Query the index
    query_engine = index.as_query_engine()
    response = query_engine.query("What's up recently?")
    print(response)

    return index


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
    return [dict(zip(columns, row)) for row in rows]


def convert_to_documents(data: List[Dict[str, Any]]) -> List[Document]:
    logger.info("Converting data to documents")
    documents = []
    for item in data:
        logger.debug(f"Processing item: {item}")
        # Convert datetime objects to strings
        for key in ["date_gmt", "modified_gmt"]:
            if isinstance(item[key], datetime):
                item[key] = item[key].isoformat()
        doc = Document(
            text=item["md_content"],
            metadata={
                "id": item["id"],
                "title": item["title"],
                "date_gmt": item["date_gmt"],
                "modified_gmt": item["modified_gmt"],
                "link": item["link"],
                "status": item["status"],
                "excerpt": item.get("excerpt", ""),
                "author_id": item["author_id"],
                "author_first_name": item["author_first_name"],
                "author_last_name": item["author_last_name"],
                "editor": item.get("editor", ""),
                "comments_count": item.get("comments_count", 0),
            },
        )
        documents.append(doc)
    logger.info(f"Converted {len(documents)} documents")
    return documents
