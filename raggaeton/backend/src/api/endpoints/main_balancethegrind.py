import logging
import json
import os
import requests
from typing import List, Optional
from datetime import datetime
from raggaeton.backend.src.api.endpoints.ingest import (
    ingest_research_data,
    generate_research_questions,
)
from raggaeton.backend.src.utils.common import base_dir
from raggaeton.backend.src.db.supabase import fetch_data, upsert_data
from raggaeton.backend.scripts.preproc import (
    convert_html_to_markdown,
)  # Import the function
from llama_index.packs.ragatouille_retriever.base import RAGatouilleRetrieverPack
from llama_index.llms.openai import OpenAI
from llama_index.core import Document
from raggaeton.backend.src.api.endpoints.tools import load_rag_query_tool
from raggaeton.backend.src.utils.error_handler import DataError
from raggaeton.backend.src.api.endpoints.agent import get_agent
from raggaeton.backend.src.utils.error_handler import InitializationError
import ast
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INDEX_PATH = "/Users/erniesg/code/erniesg/raggaeton-tia-backend/.ragatouille/colbert/indexes/balancethegrind"


def clean_content(content: str) -> str:
    # Use the convert_html_to_markdown function to clean the content
    return convert_html_to_markdown(content)


# Load the JSON data from file using base_dir
textfx_file_path = os.path.join(
    base_dir, "raggaeton", "backend", "src", "config", "textfx_examples.json"
)
with open(textfx_file_path, "r") as file:
    data = json.load(file)
    logger.info("Loaded textfx_examples successfully.")


# Function to get three random examples from each category
def get_three_random_examples(category):
    examples = data[category]["examples"]
    selected_examples = random.sample(examples, 3)  # Randomly select 3 examples
    return selected_examples


# Collect three random examples from each textfx category
textfx_categories = [
    "SIMILE",
    "EXPLODE",
    "UNEXPECT",
    "CHAIN",
    "POV",
    "ALLITERATION",
    "ACRONYM",
    "FUSE",
    "SCENE",
    "UNFOLD",
]
all_examples = {
    category: get_three_random_examples(category) for category in textfx_categories
}


def ingest_and_clean_data(research_params: dict) -> List[dict]:
    topic = research_params.get("topic", "Health & Wellbeing")
    article_types = research_params.get(
        "article_types", ["benefits", "how-to", "listicles"]
    )
    platforms = research_params.get("platforms", ["you_snippets"])
    personas = research_params.get("personas", ["general audience"])
    target_audience = research_params.get("target_audience", "global")
    limit = research_params.get("limit", 10)

    logger.info("Starting research data ingestion...")
    response = ingest_research_data(
        topic, article_types, platforms, personas, target_audience, limit
    )
    logger.info(
        f"Research data ingestion completed. Response: {str(response)[:100]}... Type: {type(response)}"
    )
    # Flatten the response to get a list of all fetched data
    fetched_data = [item for sublist in response.values() for item in sublist]
    logger.info(f"Fetched data count: {len(fetched_data)}")

    # Clean Wikipedia content and update Supabase
    for record in fetched_data:
        if record["source"] == "wikipedia":
            logger.info(
                f"Original raw content for record ID {record['id'][:8]}: {record['raw_content'][:100]}..."
            )  # Log a sample of the raw content
            logger.info(f"Type of raw content: {type(record['raw_content'])}")

            clean_content_text = clean_content(record["raw_content"])

            logger.info(
                f"Cleaned content for record ID {record['id'][:8]}: {clean_content_text[:100]}..."
            )  # Log a sample of the cleaned content
            logger.info(f"Type of cleaned content: {type(clean_content_text)}")

            record["clean_content"] = clean_content_text
            upsert_data("balancethegrind_fetched_data", [record])
            logger.info(
                f"Cleaned content for record ID {record['id'][:8]} and updated Supabase."
            )

    # Fetch updated data from Supabase
    updated_data = fetch_data("balancethegrind_fetched_data")
    logger.info(f"Fetched updated data count from Supabase: {len(updated_data)}")

    return updated_data


def prepare_documents(data: List[dict]) -> List[Document]:
    documents = []
    for item in data:
        text_content = item.get("clean_content") or item.get("raw_content")
        if text_content:
            metadata = {
                "id": item["id"],
                "title": item["title"],
                "date_fetched": item["date_fetched"],
                "created_at": item["created_at"],
                "url": item["url"],
                "author": item["author"],
                "source": item["source"],
            }
            doc = Document(text=text_content, metadata=metadata)
            documents.append(doc)
        else:
            logger.warning(
                f"Skipping item with ID {item['id']} due to missing content."
            )
    return documents


def create_ragatouille_index(
    docs: List[Document], index_name: str
) -> RAGatouilleRetrieverPack:
    logger.info(f"Checking if index path exists: {INDEX_PATH}")
    if os.path.exists(INDEX_PATH):
        logger.info(f"Using existing index at: {INDEX_PATH}")
        collection_file = os.path.join(INDEX_PATH, "collection.json")
        logger.info(f"Checking if collection file exists at: {collection_file}")
        if not os.path.exists(collection_file):
            logger.error(f"Collection file does not exist at: {collection_file}")
            raise FileNotFoundError(
                f"Collection file does not exist at: {collection_file}"
            )
        try:
            logger.info(f"Loading RAG query tool from index path: {INDEX_PATH}")
            ragatouille_pack = load_rag_query_tool(index_path=INDEX_PATH, docs=docs)
        except DataError as e:
            logger.error(f"Failed to load existing index: {e}")
            raise
    else:
        logger.info(f"Creating new index at: {INDEX_PATH}")
        index_path = os.path.join(base_dir, ".ragatouille/colbert/indexes", index_name)
        logger.info(f"New index path: {index_path}")
        if not os.path.exists(index_path):
            os.makedirs(index_path)
            logger.info(f"Created new directory at: {index_path}")

        # Create metadata files if they do not exist
        metadata_path = os.path.join(index_path, "metadata.json")
        plan_path = os.path.join(index_path, "plan.json")

        logger.info(f"Checking if metadata file exists at: {metadata_path}")
        if not os.path.exists(metadata_path):
            with open(metadata_path, "w") as f:
                json.dump(
                    {"index_name": index_name, "created_at": str(datetime.utcnow())}, f
                )
            logger.info(f"Created metadata file at: {metadata_path}")

        logger.info(f"Checking if plan file exists at: {plan_path}")
        if not os.path.exists(plan_path):
            with open(plan_path, "w") as f:
                json.dump(
                    {"index_name": index_name, "created_at": str(datetime.utcnow())}, f
                )
            logger.info(f"Created plan file at: {plan_path}")

        # Initialize RAGatouille retriever without specifying index_path
        ragatouille_pack = RAGatouilleRetrieverPack(
            documents=docs,
            llm=OpenAI(model="gpt-4o"),
            index_name=index_name,
            top_k=10,
        )
        logger.info(f"Ragatouille index created at: {index_path}")
    return ragatouille_pack


def retrieve_and_display_nodes(
    ragatouille_pack: RAGatouilleRetrieverPack, query: str
) -> List[dict]:
    retriever = ragatouille_pack.get_modules()["retriever"]
    nodes = retriever.retrieve(query)
    for node in nodes:
        logger.info(f"Retrieved node: {node}")
    return nodes


def construct_query(
    topic: str,
    keywords: List[str],
    article_types: Optional[List[str]] = None,
    personas: Optional[List[str]] = None,
    target_audience: Optional[str] = None,
) -> str:
    query = f"Research on {topic} with focus on "
    query += ", ".join(keywords)
    # if article_types:
    #     query += f" and article types: {', '.join(article_types)}"
    # if personas:
    #     query += f" for personas: {', '.join(personas)}"
    # if target_audience:
    #     query += f" targeting: {target_audience}"
    return query


def generate_draft(
    topic: str,
    article_types: List[str],
    personas: List[str],
    target_audience: str,
    context: str,
    scratchpad: str,
    desired_length: int,
):
    url = "https://erniesg--generate-svc-generate.modal.run"
    response_data = {}
    for article_type in article_types:
        payload = {
            "keyword": f"generate_{article_type}_draft",
            "topic": topic,
            "article_type": article_type,
            "personas": personas,
            "target_audience": target_audience,
            "context": context,
            "scratchpad": scratchpad,
            "desired_length": desired_length,
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()

            full_content = response.text
            token_count = response.headers.get("x-total-tokens", 0)
            draft_data = json.loads(full_content)
            response_data[article_type] = {
                "full_content": full_content,
                "token_count": token_count,
                "draft_data": draft_data,
            }
            logger.info(
                f"Generated draft for {article_type}: {json.dumps(draft_data, indent=2)}"
            )
            logger.info(f"Draft data type: {type(draft_data)}")
            logger.info(f"Full content type: {type(full_content)}")
            logger.info(f"Token count: {token_count}")

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error occurred while generating draft for {article_type}: {str(e)}"
            )
        except json.JSONDecodeError:
            logger.error(
                f"Failed to parse JSON response for generate_draft: {response.text}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error occurred while generating draft for {article_type}: {str(e)}"
            )

    return response_data


def generate_topic_sentences(
    draft: dict,
    context: str,
    scratchpad: str,
    topic: str,
    article_type: str,
    personas: List[str],
    target_audience: str,
    desired_length: int,
):
    if isinstance(draft, list):
        logger.warning("Input draft is a list. Extracting the first element.")
        draft = draft[0]

    if not isinstance(draft, dict):
        logger.error(f"Invalid draft format. Expected dict, got {type(draft)}")
        return None

    headline = draft.get("headline", "")
    thesis = draft.get("thesis", "")
    structure = draft.get("structure", [])

    url = "https://erniesg--generate-svc-generate.modal.run"
    payload = {
        "keyword": "generate_topic_sentences_from_template",
        "headline": headline,
        "thesis": thesis,
        "structure": structure,
        "context": context,
        "scratchpad": scratchpad,
        "topic": topic,
        "article_type": article_type,
        "personas": personas,
        "target_audience": target_audience,
        "desired_length": desired_length,
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(
            f"Failed to generate topic sentences for {headline}: {response.text}"
        )
        return None


def edit_content(
    draft: dict,
    topic_sentences: dict,
    context: str,
    scratchpad: str,
    topic: str,
    article_type: str,
    personas: List[str],
    target_audience: str,
    desired_length: int,
    initial_draft_outline: Optional[str] = None,
):
    if isinstance(draft, list):
        logger.warning("Input draft is a list. Extracting the first element.")
        draft = draft[0]

    if not isinstance(draft, dict):
        logger.error(f"Invalid draft format. Expected dict, got {type(draft)}")
        return None

    if isinstance(topic_sentences, list):
        logger.warning("Input topic_sentences is a list. Extracting the first element.")
        topic_sentences = topic_sentences[0]

    if not isinstance(topic_sentences, dict):
        logger.error(
            f"Invalid topic_sentences format. Expected dict, got {type(topic_sentences)}"
        )
        return None

    headline = draft.get("headline", "")
    thesis = draft.get("thesis", "")
    subheadings = topic_sentences.get("content_blocks", [])

    url = "https://erniesg--generate-svc-generate.modal.run"
    payload = {
        "keyword": "edit_content",
        "headline": headline,
        "thesis": thesis,
        "subheadings": subheadings,
        "context": context,
        "scratchpad": scratchpad,
        "topic": topic,
        "article_type": article_type,
        "personas": personas,
        "target_audience": target_audience,
        "desired_length": desired_length,
        "initial_draft_outline": initial_draft_outline,  # Add the initial_draft_outline to the payload
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        edited_content = response.json()
        # Convert edited content to a string
        edited_content_str = json.dumps(edited_content, indent=2)
        logger.info(f"Edited content (str): {edited_content_str}")
        return edited_content
    else:
        logger.error(f"Failed to edit content for {headline}: {response.text}")
        return None


def main(research_params: dict, demo_mode: bool = False):
    if demo_mode:
        logger.info("Demo mode is enabled. Skipping ingestion and research steps.")
        index_path = os.path.join(
            base_dir, ".ragatouille/colbert/indexes/balancethegrind"
        )
        agent = get_agent(index_path=index_path)
        if agent is None:
            raise InitializationError("Agent loading failed. Agent is None.")
        else:
            logger.info(f"Agent loaded successfully: {type(agent)}")
        return

    topic = research_params.get("topic", "Health & Wellbeing")
    article_types = research_params.get(
        "article_types", ["benefits", "how-to", "listicles"]
    )
    platforms = research_params.get(
        "platforms", ["you.com"]
    )  # Ensure platforms are correctly set
    personas = research_params.get("personas", ["general audience"])
    target_audience = research_params.get("target_audience", "global")
    scratchpad = research_params.get("scratchpad", "")

    # Generate research questions
    research_questions = generate_research_questions(
        topic, article_types, platforms, personas, target_audience
    )
    keywords = [
        kw for platform in research_questions for kw in platform.get("keywords", [])
    ]

    # Log the keywords used for the query
    logger.info(f"Keywords for query: {keywords}")

    # Ingest and clean data
    updated_data = ingest_and_clean_data(research_params)

    # Prepare documents for indexing
    documents = prepare_documents(updated_data)

    # Create or load RAGatouille index
    ragatouille_pack = create_ragatouille_index(documents, "balancethegrind")

    # Construct the query using the topic and keywords
    query = construct_query(topic, keywords, article_types, personas, target_audience)
    logger.info(f"Constructed query: {query}")

    # Retrieve and display nodes
    nodes = retrieve_and_display_nodes(ragatouille_pack, query)

    # Prepare context for listicle draft generation
    context = "\n".join([node.text for node in nodes])
    logger.info(f"Passing scratchpad to generate_draft: {scratchpad}")

    # Generate drafts
    drafts = generate_draft(
        topic=topic,
        article_types=article_types,
        personas=personas,
        target_audience=target_audience,
        context=context,
        scratchpad=scratchpad,
        desired_length=800,
    )
    logger.info(f"Type of drafts: {type(drafts)}")
    logger.info(f"Length of drafts: {len(drafts)}")
    logger.info(f"Drafts key-value pairs: {drafts.keys()}")
    for article_type, draft_info in drafts.items():
        logger.info(f"Processing draft for article type: {article_type}")
        full_content = draft_info["full_content"]

        # Check if full_content is a string that looks like a list
        if isinstance(full_content, str) and full_content.startswith("["):
            try:
                # Safely evaluate the string to convert it into a list
                full_content = ast.literal_eval(full_content)
            except ValueError as e:
                logger.error(f"Error converting full_content string to list: {e}")
                continue
        # Now handle the list assuming it contains a JSON string and a token count
        if isinstance(full_content, list) and len(full_content) == 2:
            json_string, token_count = full_content
            try:
                draft_data = json.loads(json_string)
                logger.info(f"Draft data type: {type(draft_data)}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {json_string}")
                continue
            # Extract and log the headlines
            headlines = draft_data.get("headlines", [])
            for headline_data in headlines:
                logger.info(f"Processing headline: {headline_data.get('headline')}")
                process_headline(
                    headline_data,
                    context,
                    scratchpad,
                    topic,
                    article_type,
                    personas,
                    target_audience,
                )
        else:
            logger.error(f"Unexpected format for full_content: {full_content}")


def generate_full_article_from_template(request: dict):
    url = "https://erniesg--generate-svc-generate.modal.run"
    payload = {
        "keyword": "generate_full_article_from_template",
        "topic": request["topic"],
        "article_type": request["article_type"],
        "personas": request["personas"],
        "target_audience": request["target_audience"],
        "context": request["context"],
        "scratchpad": request["scratchpad"],
        "desired_length": request["desired_length"],
        "edited_draft_outline": request["edited_draft_outline"],
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error occurred while generating full article: {str(e)}")
        return ""
    except Exception as e:
        logger.error(
            f"Unexpected error occurred while generating full article: {str(e)}"
        )
        return ""


def polish_content(request: dict):
    url = "https://erniesg--generate-svc-generate.modal.run"
    payload = {
        "keyword": "polish_content",
        "topic": request["topic"],
        "article_type": request["article_type"],
        "personas": request["personas"],
        "target_audience": request["target_audience"],
        "context": request["context"],
        "scratchpad": request["scratchpad"],
        "desired_length": request["desired_length"],
        "edited_draft_outline": request["edited_draft_outline"],
        "textfx": all_examples,
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error occurred while polishing content: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error occurred while polishing content: {str(e)}")
        return ""


def process_headline(
    headline_data, context, scratchpad, topic, article_type, personas, target_audience
):
    # Convert the structure list to a single string
    structure_list = headline_data.get("structure", [])
    structure_str = "\n".join(
        [str(block["details"]) for block in structure_list if "details" in block]
    )

    # Update the headline_data with the converted structure string
    headline_data["structure"] = structure_str

    logger.info(
        f"Processing headline for {article_type}: {json.dumps(headline_data, indent=2)}"
    )
    topic_sentences = generate_topic_sentences(
        draft=headline_data,
        context=context,
        scratchpad=scratchpad,
        topic=topic,
        article_type=article_type,
        personas=personas,
        target_audience=target_audience,
        desired_length=800,
    )

    if topic_sentences is None:
        return

    # Edit content for the current headline
    edited_content = edit_content(
        draft=headline_data,
        topic_sentences=topic_sentences,
        context=context,
        scratchpad=scratchpad,
        topic=topic,
        article_type=article_type,
        personas=personas,
        target_audience=target_audience,
        desired_length=800,
        initial_draft_outline=headline_data.get(
            "structure"
        ),  # Assuming 'structure' is the initial draft outline
    )
    # pdb.set_trace()
    if edited_content:
        # Deserialize the JSON string
        if isinstance(edited_content, list) and len(edited_content) == 2:
            json_string, token_count = edited_content
            try:
                edited_content = json.loads(json_string)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {json_string}")
                return
        logger.info(f"Edited content (JSON): {json.dumps(edited_content, indent=2)}")
        generate_request = {
            "topic": topic,
            "article_type": article_type,
            "personas": personas,
            "target_audience": target_audience,
            "context": context,
            "scratchpad": scratchpad,
            "desired_length": 800,
            "edited_draft_outline": edited_content,  # Pass the deserialized edited content as a JSON object
        }
        logger.info(
            f"Generate request payload: {json.dumps(generate_request, indent=2)}"
        )  # Log the generate request payload
        full_article = generate_full_article_from_template(generate_request)
        logger.info(f"Generated full article: {full_article}")

        # Polish content
        polish_request = {
            "topic": topic,
            "article_type": article_type,
            "personas": personas,
            "target_audience": target_audience,
            "context": context,
            "scratchpad": scratchpad,
            "desired_length": 800,
            "edited_draft_outline": edited_content,  # Pass the deserialized edited content as a JSON object
        }
        logger.info(
            f"Polish request payload: {json.dumps(polish_request, indent=2)}"
        )  # Log the polish request payload
        polished_content = polish_content(polish_request)
        logger.info(f"Polished content: {polished_content}")

    else:
        logger.error(f"Failed to edit content for {article_type}")


if __name__ == "__main__":
    research_params = {
        "topic": "Health & Wellbeing",
        "article_types": ["benefits"],
        "platforms": ["you.com"],  # Ensure platforms are correctly set
        "personas": ["C-level execs"],
        "target_audience": "AU",
        "limit": 2,
        "scratchpad": "i saw an ant move a flower on a hike. it was trying with all its might.",
    }
    main(research_params)  # Set demo_mode to True to activate demo mode
