from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.core import VectorStoreIndex
from raggaeton.backend.src.utils.common import load_config
import logging

logger = logging.getLogger(__name__)


def retrieve_stored_index():
    config = load_config()
    db_params = {
        "user": config["supabase_user"],
        "password": config["supabase_pw"],
        "host": config["supabase_host"],
        "port": "5432",
        "dbname": "postgres",
    }

    postgres_connection_string = (
        f"postgresql://{db_params['user']}:{db_params['password']}@"
        f"{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    )
    vector_store = SupabaseVectorStore(
        postgres_connection_string=postgres_connection_string,
        collection_name=config["index_name"],
    )

    # Retrieve the index
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    # Log the number of items in the vector store
    num_items = len(vector_store)
    logger.info(f"Number of items in the vector store: {num_items}")

    # Log some sample items
    sample_items = vector_store[:5]  # Retrieve the first 5 items
    logger.info(f"Sample items from the vector store: {sample_items}")

    return index
