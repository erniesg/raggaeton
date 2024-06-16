import requests
from raggaeton.backend.src.db.supabase import upsert_data
from raggaeton.backend.src.utils.common import config_loader
from raggaeton.backend.src.api.endpoints.fetch import (
    fetch_data_from_you,
    fetch_data_from_wikipedia,
    fetch_data_from_google_news,
)
import json
import logging
from datetime import datetime


# Load configuration and secrets
config = config_loader.get_config()
secrets = config_loader.secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest(source, limit=None):
    pass


def extract_relevant_data(page_data):
    return [
        {
            "id": post["id"],
            "title": post["title"],
            "content": post["content"],
            "date_gmt": post["date_gmt"],
            "modified_gmt": post["modified_gmt"],
            "link": post["link"],
            "status": post["status"],
            "excerpt": post.get("excerpt", ""),
            "author_id": post["author"]["id"],
            "author_first_name": post["author"]["first_name"],
            "author_last_name": post["author"]["last_name"],
            "editor": post.get("editor", ""),
            "comments_count": post.get("comments_count", 0),
        }
        for post in page_data["posts"]
    ]


def save_to_database(posts, batch_number, page_number):
    data = [
        {"batch_number": batch_number, "page_number": page_number, **post}
        for post in posts
    ]
    upsert_data(config["table_posts"], data)


def generate_research_questions(
    topic, article_types, platforms, personas, target_audience
):
    url = "https://erniesg--generate-svc-generate.modal.run"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {secrets['MODAL_API_KEY']}",
    }
    payload = {
        "keyword": "generate_research_questions",
        "topic": topic,
        "article_types": article_types,
        "platforms": platforms,
        "personas": personas,
        "target_audience": target_audience,
    }
    # Log the URL and payload for debugging
    logger.info(f"Request URL: {url}")
    logger.info(f"Request payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_json = response.json()
    logger.info(f"Response from generate service: {response_json}")

    # Assuming the response structure is a list of dictionaries
    research_questions = json.loads(response_json[0])["platforms"]

    return research_questions


def ingest_research_data(
    topic, article_types, platforms, personas, target_audience, limit=None
):
    research_questions = generate_research_questions(
        topic, article_types, platforms, personas, target_audience
    )
    results = {}

    for platform_data in research_questions:
        platform = platform_data["platform"]
        keywords = platform_data["keywords"]

        if platform == "you.com":
            # Handle both sources for you.com
            sources = ["you_snippets"]
            for source in sources:
                you_data = fetch_data_from_you(
                    keywords, limit, target_audience, source=source
                )
                logger.info(f"Fetched data from {source}: {len(you_data)} items")
                save_fetched_data(you_data, source)
                if source not in results:
                    results[source] = []
                results[source].extend(you_data)
        elif platform == "wikipedia":
            wikipedia_data = fetch_data_from_wikipedia(keywords, limit)
            logger.info(f"Fetched data from Wikipedia: {len(wikipedia_data)} items")
            save_fetched_data(wikipedia_data, "wikipedia")
            results["wikipedia"] = wikipedia_data
        elif platform == "serp_google_news":
            google_news_data = fetch_data_from_google_news(keywords, limit)
            logger.info(f"Fetched data from Google News: {len(google_news_data)} items")
            save_fetched_data(google_news_data, "serp_google_news")
            results["serp_google_news"] = google_news_data
        else:
            logger.warning(f"Unsupported platform: {platform}")

    logger.info(f"Total items fetched: {sum(len(data) for data in results.values())}")
    return results


def save_fetched_data(data, platform):
    logger.info(f"Incoming data for {platform}: {data}")
    formatted_data = []
    for item in data:
        formatted_data.append(
            {
                "id": item["id"],  # Use the ID generated in the fetch functions
                "title": item.get("title") or "N/A",
                "date_fetched": item.get("date_fetched")
                or datetime.utcnow().isoformat(),
                "created_at": item.get("created_at") or datetime.utcnow().isoformat(),
                "author": item.get("author", "N/A"),
                "raw_content": item.get("raw_content") or "N/A",
                "url": item.get("url") or "N/A",
                "source": platform,  # Add the source of the data
            }
        )
    logger.info(f"Formatted data to be saved for {platform}: {formatted_data}")

    upsert_data(config["table_fetched_data"], formatted_data)
