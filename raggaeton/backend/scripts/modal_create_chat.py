import os
import logging
import modal
from llama_index.core import Settings, StorageContext
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.core import load_index_from_storage

from llama_index.core import set_global_handler

set_global_handler("deepeval")

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Define the Modal image with necessary dependencies
chat_image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "requests",
    "supabase",
    "PyYAML",
    "python-dotenv",
    "llama-index",
    "llama-index-llms-openai",
    "llama-index-llms-anthropic",
    "llama-index-readers-database",
    "llama-index-embeddings-huggingface",
    "llama-index-vector-stores-supabase",
    "llama-index-callbacks-deepeval",
    "psycopg2-binary",
)

# Define the Modal app
app = modal.App(
    name="raggaeton-chat-app",
    image=chat_image,
    secrets=[
        modal.Secret.from_name("my-postgres-secret"),
        modal.Secret.from_name("my-openai-secret"),
    ],
)

# Define a volume for caching the embedding model and storing the index
index_volume = modal.Volume.from_name("index-storage", create_if_missing=True)

# Mount the local directory
raggaeton_mount = modal.Mount.from_local_dir(
    local_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
    remote_path="/app/raggaeton",
    condition=lambda pth: not pth.endswith(".env")
    and not pth.endswith("modal_create_chat.py"),
    recursive=True,
)


@app.function(
    mounts=[raggaeton_mount],
    volumes={"/cache": index_volume},
    secrets=[
        modal.Secret.from_name("my-postgres-secret"),
        modal.Secret.from_name("my-openai-secret"),
    ],
    gpu="any",
    _allow_background_volume_commits=True,
)
def create_chat(mode, llm_name, config=None):
    import sys

    sys.path.insert(0, "/app/raggaeton")

    from raggaeton.backend.src.utils.common import load_config
    from raggaeton.backend.src.db.vecs import retrieve_stored_index

    config = load_config()

    persist_dir = "/cache/index"
    storage_context = StorageContext.from_defaults(
        docstore=SimpleDocumentStore.from_persist_dir(persist_dir=persist_dir),
        vector_store=SupabaseVectorStore.from_persist_dir(persist_dir=persist_dir),
    )
    index = load_index_from_storage(storage_context, index_id="my_index")

    index = retrieve_stored_index()
    llm = initialize_llm(llm_name, config)

    if mode == "best":
        return index.as_chat_engine(chat_mode="best", llm=llm, verbose=True)
    else:
        raise ValueError(f"Unsupported chat mode: {mode}")


def initialize_llm(llm_name, config):
    if llm_name == "openai":
        return OpenAI(model=config["llm"]["models"][0]["model_name"])
    elif llm_name == "anthropic":
        return Anthropic(model=config["llm"]["models"][1]["model_name"])
    else:
        raise ValueError(f"Unsupported LLM: {llm_name}")


@app.local_entrypoint()
def main():
    from raggaeton.backend.src.utils.common import load_config

    config = load_config()

    embed_model = HuggingFaceEmbedding(
        model_name="Alibaba-NLP/gte-base-en-v1.5", trust_remote_code=True
    )
    Settings.embed_model = embed_model

    chat_engine = create_chat.remote("best", "openai", config)

    response = chat_engine.chat("What's up recently?")
    print("Response:", response)

    response = chat_engine.chat("Why are Asian sports stars getting into VC space?")
    print("Response:", response)

    response = chat_engine.chat("Tell me about Grab’s profitability.")
    print("Response:", response)


if __name__ == "__main__":
    main()
