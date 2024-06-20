import requests
import os
from raggaeton.backend.src.schemas.research import (
    GenerateResearchQuestionsRequest,
    DoResearchRequest,
)
from raggaeton.backend.src.api.services.index import (
    create_ragatouille_index,
    retrieve_nodes,
    construct_query,
)
from raggaeton.backend.src.db.supabase import upsert_data, fetch_data
from raggaeton.backend.src.schemas.content import (
    GenerateHeadlinesRequest,
    GenerateDraftRequest,
)
from llama_index.core import Document, Settings
from raggaeton.backend.src.utils.common import (
    config_loader,
    error_handling_context,
    find_project_root,
)
from raggaeton.backend.src.utils.utils import truncate_log_message
import logging

logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000/api"
TIMEOUT = 120  # Increased timeout to 120 seconds


def set_document_settings():
    config = config_loader.config
    chunk_size = config["document"]["chunk_size"][0]  # Use the first setting
    overlap = config["document"]["overlap"][0]  # Use the first setting
    Settings.chunk_size = chunk_size
    Settings.chunk_overlap = overlap
    logger.debug(f"Document settings set: chunk_size={chunk_size}, overlap={overlap}")


def main():
    with error_handling_context():
        # Define common parameters
        topics = ["Hiking", "Climbing Fu Gai Mountain in Zhejiang", "floating cap"]
        article_types = ["travel"]
        optional_params = {
            "desired_length": 600,
            "scratchpad": "I saw an ant try to move a flower on the hike, it was doing so with all its might.\nWhen not doing gradient descent, an A.I. engineer had lots of fun climbing a physical mountain. I took a challenging route and ended up climbing over rocks and caves.",
        }

        # Step 1: Generate research questions for both you.com and Obsidian
        logger.info("Generating research questions...")
        research_request = GenerateResearchQuestionsRequest(
            topics=topics,
            article_types=article_types,
            platforms=["you.com", "obsidian"],
            optional_params=optional_params,
        )
        response = requests.post(
            f"{API_BASE_URL}/generate-research-questions",
            json=research_request.dict(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        research_questions_response = response.json()
        logger.info("Generated Research Questions: %s", research_questions_response)

        # Step 2: Do research for both you.com and Obsidian
        logger.info("Performing research...")
        do_research_request = DoResearchRequest(
            research_questions=research_questions_response["research_questions"],
            optional_params=optional_params,
        )
        response = requests.post(
            f"{API_BASE_URL}/do-research",
            json=do_research_request.dict(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        research_results_response = response.json()
        logger.debug("Research Results: %s", research_results_response)

        # Step 3: Extract you.com and Obsidian snippets
        logger.info("Extracting snippets...")
        you_com_data = (
            research_results_response.get("fetched_research", {})
            .get("you.com", {})
            .get("results", [])
        )
        logger.info(
            "Extracted you.com data: type=%s, length=%d, data=%s",
            type(you_com_data).__name__,
            len(you_com_data),
            truncate_log_message(str(you_com_data), length=500),
        )

        obsidian_data = (
            research_results_response.get("fetched_research", {})
            .get("obsidian", {})
            .get("results", [])
        )
        logger.info(
            "Extracted Obsidian data: type=%s, length=%d, data=%s",
            type(obsidian_data).__name__,
            len(obsidian_data),
            truncate_log_message(str(obsidian_data), length=500),
        )

        # Step 4: Save you.com and Obsidian data to Supabase
        logger.info("Saving data to Supabase...")
        upsert_data("research_results", you_com_data)
        upsert_data("research_results", obsidian_data)

        # Step 5: Retrieve data from Supabase
        logger.info("Retrieving data from Supabase...")
        saved_research_results = fetch_data("research_results")
        logger.debug("Saved Research Results: %s", saved_research_results)

        # Step 6: Set document settings from config
        logger.info("Setting document settings...")
        set_document_settings()

        # Step 7: Prepare documents for indexing
        logger.info("Preparing documents for indexing...")
        documents = [
            Document(text=item["raw_content"], metadata=item)
            for item in saved_research_results
        ]

        # Step 8: Check if the index path exists
        base_dir = find_project_root(os.path.dirname(__file__))
        index_name = config_loader.config["index_name"]
        index_path = os.path.join(
            base_dir, ".ragatouille", "colbert", "indexes", index_name
        )

        if os.path.exists(index_path):
            logger.info(f"Index path exists: {index_path}")
            ragatouille_pack = create_ragatouille_index(
                documents, index_name, index_path=index_path
            )
        else:
            logger.info("Index path does not exist. Creating new index...")
            ragatouille_pack = create_ragatouille_index(documents, index_name)

        # Step 9: Construct the query using the topics
        logger.info("Constructing query...")
        query = construct_query(topics)
        nodes = retrieve_nodes(ragatouille_pack, query)
        logger.info("Nodes returned: %s", truncate_log_message(str(nodes), length=500))
        context = "\n".join([node.text for node in nodes])

        # Step 10: Generate headlines
        logger.info("Generating headlines...")
        headlines_request = GenerateHeadlinesRequest(
            article_types="travel",
            topics=["Climbing Fu Gai Mountain in Zhejiang"],
            context={"context": context},
            optional_params=optional_params,
        )
        logger.info("Generate Headlines Request: %s", headlines_request.dict())
        response = requests.post(
            f"{API_BASE_URL}/generate-headlines",
            json=headlines_request.dict(),
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        headlines_response = response.json()
        logger.info("Generated Headlines: %s", headlines_response)

        # Step 11: Generate drafts for each headline
        logger.info("Generating drafts for each headline...")
        for headline_data in headlines_response["headlines"]:
            draft_request = GenerateDraftRequest(
                topics=topics,
                context={"context": context},
                headline=headline_data["headline"],
                hook=headline_data["hook"],
                thesis=headline_data["thesis"],
                article_type=headline_data["article_type"],
                optional_params=optional_params,
            )
            logger.debug("Generate Draft Request: %s", draft_request.dict())
            response = requests.post(
                f"{API_BASE_URL}/generate-draft",
                json=draft_request.dict(),
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            draft_response = response.json()
            logger.info("Generated Draft: %s", draft_response)
            logger.debug("Draft Response Type: %s", type(draft_response))

            # Log the raw response
            logger.debug("Raw Draft Response: %s", response.text)

            # Log the draft outlines specifically
            for draft in draft_response.get("drafts", []):
                logger.debug("Draft Outlines: %s", draft.get("draft_outlines", []))


if __name__ == "__main__":
    main()
