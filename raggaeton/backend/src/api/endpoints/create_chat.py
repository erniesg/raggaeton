from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from raggaeton.backend.src.utils.common import load_config
from raggaeton.backend.src.db.vecs import retrieve_stored_index


def initialize_llm(llm_name, config):
    if llm_name == "openai":
        return OpenAI(model=config["llm"]["models"][0]["model_name"])
    elif llm_name == "anthropic":
        return Anthropic(model=config["llm"]["models"][1]["model_name"])
    else:
        raise ValueError(f"Unsupported LLM: {llm_name}")


def create_chat(mode, llm_name, embedding_model_name, config):
    index = retrieve_stored_index(embedding_model_name)
    llm = initialize_llm(llm_name, config)
    if mode == "best":
        return index.as_chat_engine(chat_mode="best", llm=llm, verbose=True)
    else:
        raise ValueError(f"Unsupported chat mode: {mode}")


def main():
    config = load_config()
    embedding_model_name = "Alibaba-NLP/gte-base-en-v1.5"
    chat_engine = create_chat("best", "openai", embedding_model_name, config)

    response = chat_engine.chat("Tell me something about business tools.")
    print("Response:", response)

    response = chat_engine.chat("Why are Asian sports stars getting into VC space?")
    print("Response:", response)

    response = chat_engine.chat("Tell me about Grab’s profitability.")
    print("Response:", response)


if __name__ == "__main__":
    main()
