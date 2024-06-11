import requests
from raggaeton.backend.src.db.supabase import supabase, upsert_data
from raggaeton.backend.src.utils.common import base_dir, config_loader
from raggaeton.backend.src.api.endpoints.fetch import (
    fetch_data_from_you,
    fetch_data_from_wikipedia,
    fetch_data_from_google_news,
)
import json
import os
import logging
from datetime import datetime


# Load configuration and secrets
config = config_loader.get_config()
secrets = config_loader.secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest(source, limit=None):
    if source == "tia":
        return ingest_tia(limit=limit)
    else:
        raise ValueError("Unsupported source")


def ingest_tia(limit=None):  # Add a limit parameter for testing
    metadata = fetch_metadata(page=1)
    total_pages = metadata["total_pages"]
    batch_size = 30  # Default batch size for TIA

    batches = generate_batches(total_pages, batch_size, limit=limit)
    for batch_number, batch in enumerate(batches, start=1):
        log_batch_initiation(batch_number)
        process_batch(batch_number, batch)


def fetch_metadata(page):
    # Path to the cookie file
    cookie_path = os.path.join(base_dir, "raggaeton/backend/src/config/tia_cookie.txt")

    # Read the cookie text from the file
    with open(cookie_path, "r") as file:
        cookie_text = file.read().strip()

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Cookie": cookie_text,
        "Host": "www.techinasia.com",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }
    response = requests.get(
        f"https://www.techinasia.com/wp-json/techinasia/2.0/posts?page={page}",
        headers=headers,
    )
    logging.info(
        f"Fetched page {response.json()['current_page']} with {len(response.json()['posts'])} posts."
    )

    return response.json()


def generate_batches(total_pages, batch_size, limit=None):
    if limit is None:
        limit = total_pages
    else:
        limit = min(limit, total_pages)  # Ensure limit does not exceed total_pages
    batches = []
    for i in range(0, limit, batch_size):
        batch = list(range(i + 1, min(i + batch_size + 1, limit + 1)))
        batches.append(batch)
    return batches


def process_batch(batch_number, batch):
    for page_number in batch:
        try:
            page_data = fetch_metadata(page_number)  # Use fetch_metadata directly
            posts = extract_relevant_data(page_data)
            if posts:
                save_to_database(posts, batch_number, page_number)
                log_status(batch_number, page_number, "done")
            else:
                log_status(batch_number, page_number, "no posts")
        except Exception as e:
            log_status(batch_number, page_number, f"error: {str(e)}")


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


def retry_processing():
    # Fetch all pages that are not marked as 'done'
    not_done_pages = (
        supabase.table(config["table_page_status"])
        .select("*")
        .neq("status", "done")
        .execute()
    )

    # Group pages by batch number
    batches_to_process = {}
    for page in not_done_pages.data:
        batch_number = page["batch_number"]
        if batch_number not in batches_to_process:
            batches_to_process[batch_number] = []
        batches_to_process[batch_number].append(page["page_number"])

    # Process each batch
    for batch_number, pages in batches_to_process.items():
        process_batch(batch_number, pages)


def log_batch_initiation(batch_number):
    supabase.table(config["table_batch_log"]).insert(
        {"batch_number": batch_number, "status": "started"}
    ).execute()


def log_status(batch_number, page_number, status):
    supabase.table(config["table_page_status"]).upsert(
        {"batch_number": batch_number, "page_number": page_number, "status": status}
    ).execute()


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
