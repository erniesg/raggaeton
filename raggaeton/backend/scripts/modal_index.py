import os
import logging
import modal
from llama_index.core import Settings
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore
from raggaeton.backend.src.db.supabase import fetch_data

logger = logging.getLogger(__name__)
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
    "llama-index-packs-ragatouille-retriever",
    "ragatouille",
)

app = modal.App(name="raggaeton-index-app", image=index_image)

index_volume = modal.Volume.from_name("index-storage", create_if_missing=True)

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

    from raggaeton.backend.src.utils.utils import convert_to_documents

    os.getenv("OPENAI_API_KEY")

    logger.info(f"Index name: {index_name}")
    logger.info(f"Embedding model: {embedding_model}")
    logger.info(f"Chunk size: {chunk_size}")
    logger.info(f"Overlap: {overlap}")
    logger.info(f"Dimension: {dimension}")

    Settings.chunk_size = chunk_size
    Settings.chunk_overlap = overlap

    db_params = {
        "host": os.getenv("PGHOST"),
        "port": os.getenv("PGPORT"),
        "user": os.getenv("PGUSER"),
        "password": os.getenv("PGPASSWORD"),
        "dbname": os.getenv("PGDATABASE"),
    }
    rows = fetch_data("tia_posts", limit=limit)

    documents = convert_to_documents(rows)

    logger.info(f"Retrieved {len(documents)} documents from the database.")
    logger.info(
        f"Document sample: {documents[0] if documents else 'No documents retrieved'}"
    )

    embed_model = HuggingFaceEmbedding(
        model_name=embedding_model, trust_remote_code=True
    )
    Settings.embed_model = embed_model

    vector_store = SupabaseVectorStore(
        postgres_connection_string=f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}",
        collection_name=index_name,
        dimension=dimension,
    )
    logger.info("Vector store created")

    pipeline = IngestionPipeline(
        transformations=[MarkdownNodeParser(), embed_model],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
    )
    logger.info("Pipeline created")

    pipeline.run(documents=documents)

    logger.info("Documents processed and summary index created")

    return documents
