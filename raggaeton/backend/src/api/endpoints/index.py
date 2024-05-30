import os
from llama_index.core import Document
from llama_index.readers.database import DatabaseReader
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.supabase import SupabaseVectorStore
from raggaeton.backend.src.utils.common import load_config


def create_index(
    index_name=None,
    embedding_model=None,
    chunk_size=None,
    overlap=None,
    dimension=None,
    config=None,
    limit=10,
):
    # Use config defaults if parameters are not provided
    if config is None:
        config = load_config()

    index = index_name or config["index_name"]
    embedding_model = embedding_model or config["embedding"]["models"][0]
    chunk_size = chunk_size or config["document"]["chunk_size"][0]
    overlap = overlap or config["document"]["overlap"][0]
    dimension = dimension or config["embedding"]["dimension"][0]

    # Load data from Supabase with a limit
    db_params = {
        "scheme": "postgresql",
        "host": config["supabase_host"],
        "port": "5432",
        "user": config["supabase_user"],
        "password": os.getenv("SUPABASE_PW"),
        "dbname": "postgres",
    }
    reader = DatabaseReader(**db_params)
    documents = reader.load_data(
        query=f"SELECT * FROM {config['table_posts']} LIMIT {limit}"
    )

    # Create the embedding model
    embed_model = HuggingFaceEmbedding(
        model_name=embedding_model, trust_remote_code=True
    )

    # Create the vector store
    vector_store = SupabaseVectorStore(
        postgres_connection_string=f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}",
        collection_name=index_name,
        dimension=dimension,
    )

    # Create the pipeline with transformations
    pipeline = IngestionPipeline(
        node_parser=MarkdownNodeParser(),
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
        embedding_model=embed_model,
        ingestion_cache=IngestionCache(),
    )

    # Process documents
    for doc in documents:
        metadata = {
            "id": doc["id"],
            "title": doc["title"],
            "date_gmt": doc["date_gmt"],
            "modified_gmt": doc["modified_gmt"],
            "link": doc["link"],
            "status": doc["status"],
            "excerpt": doc.get("excerpt", ""),
            "author_id": doc["author_id"],
            "author_first_name": doc["author_first_name"],
            "author_last_name": doc["author_last_name"],
            "editor": doc.get("editor", ""),
            "comments_count": doc.get("comments_count", 0),
        }
        document = Document(text=doc["md_content"], metadata=metadata)
        pipeline.process_document(document)

    # Save the index
    index = pipeline.save_index(index_name)

    # Query the index
    query_engine = index.as_query_engine()
    response = query_engine.query("What's up recently?")
    print(response)

    return index


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create an index with custom settings."
    )
    parser.add_argument("--index_name", type=str, help="Name of the index")
    parser.add_argument(
        "--chunk_size", type=int, help="Chunk size for document splitting"
    )
    parser.add_argument(
        "--overlap", type=int, help="Overlap size for document splitting"
    )
    parser.add_argument(
        "--embedding_model", type=str, help="Name of the embedding model"
    )
    parser.add_argument(
        "--dimension", type=int, help="Dimension of the embedding vectors"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Limit the number of rows to load"
    )
    args = parser.parse_args()

    config = load_config()
    index = create_index(
        args.index_name,
        args.embedding_model,
        args.chunk_size,
        args.overlap,
        args.dimension,
        config,
        args.limit,
    )

# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create an index with custom settings."
    )
    parser.add_argument("--index_name", type=str, help="Name of the index")
    parser.add_argument(
        "--chunk_size", type=int, help="Chunk size for document splitting"
    )
    parser.add_argument(
        "--overlap", type=int, help="Overlap size for document splitting"
    )
    parser.add_argument(
        "--embedding_model", type=str, help="Name of the embedding model"
    )
    parser.add_argument(
        "--dimension", type=int, help="Dimension of the embedding vectors"
    )
    args = parser.parse_args()

    config = load_config()

    # index = create_index(
    #     index_name, embedding_model, chunk_size, overlap, dimension, config
    # )
