import requests
import serpapi
import logging
from raggaeton.backend.src.utils.common import config_loader
from datetime import datetime
import uuid
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load secrets
secrets = config_loader.secrets


def fetch_data_from_you(
    keywords, limit=10, target_audience="us", source="you_snippets"
):
    api_key = os.getenv("YDC_API_KEY")
    headers = {"X-API-Key": api_key}

    if source == "you.com":
        url = "https://api.ydc-index.io/news"
        params = {"q": keywords, "count": limit, "country": target_audience}
    else:  # Default to "you_snippets"
        url = "https://api.ydc-index.io/search"
        params = {"query": keywords, "count": limit, "country": target_audience}

    logger.info(f"Fetching data from {source} with URL: {url}")
    response = requests.get(url, headers=headers, params=params)
    logger.info(f"Response status code: {response.status_code}")
    response.raise_for_status()
    results = (
        response.json()["hits"]
        if source == "you_snippets"
        else response.json()["news"]["results"]
    )

    data = []
    for result in results:
        if source == "you_snippets":
            snippets = result.get("snippets", [])
            raw_content = (
                " ".join(snippets) if snippets else result.get("description", "")
            )
        else:
            raw_content = result.get("description")

        data.append(
            {
                "id": str(uuid.uuid4()),  # Always generate a unique ID
                "title": result.get("title"),
                "date_fetched": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),  # Ensure correct date format
                "author": result.get("author", "N/A"),  # Assuming author field exists
                "raw_content": raw_content,  # Use the appropriate content
                "url": result.get("url"),
                "source": source,  # Add the source of the data
            }
        )
    logger.info(f"Sample response from {source}: {data[0]}")
    return data


def fetch_data_from_wikipedia(keywords, limit=10):
    wikipedia_data = []
    for keyword in keywords:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "srlimit": limit,
        }
        response = requests.get("https://en.wikipedia.org/w/api.php", params=params)
        search_results = response.json().get("query", {}).get("search", [])

        for result in search_results:
            page_title = result["title"]
            page_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
            parse_params = {
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text",
            }
            parse_response = requests.get(
                "https://en.wikipedia.org/w/api.php", params=parse_params
            )
            parse_data = parse_response.json()
            logger.info(f"Parsed data: {parse_data}")

            content = parse_data.get("parse", {}).get("text", {}).get("*", "")
            if "From Wikipedia, the free encyclopedia" in content:
                content = content.split("From Wikipedia, the free encyclopedia")[
                    1
                ].strip()

            wikipedia_data.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": page_title,
                    "date_fetched": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "author": "Wikipedia",
                    "raw_content": content,
                    "url": page_url,
                    "source": "wikipedia",  # Add the source of the data
                }
            )
            logger.info(f"Appended data: {wikipedia_data[-1]}")

    return wikipedia_data


def fetch_data_from_google_news(keywords, limit=10):
    logger.info(f"Fetching data from Google News: {keywords}")

    google_news_data = []
    api_key = secrets[
        "SERP_API_KEY"
    ]  # Use the SERP_API_KEY from the environment variables
    for keyword in keywords:
        params = {
            "api_key": api_key,
            "engine": "google_news",
            "gl": "au",
            "q": keyword,
            "num": limit,  # Limit the number of news results
        }
        logger.info(f"Fetching data from Google News with params: {params}")

        results = serpapi.search(params)

        for result in results.get("news_results", []):
            google_news_data.append(
                {
                    "id": str(uuid.uuid4()),  # Always generate a unique ID
                    "title": result.get("title"),
                    "date_fetched": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),  # Ensure correct date format
                    "author": result.get("source", {}).get("name", "N/A"),
                    "raw_content": result.get("snippet"),
                    "url": result.get("link"),
                    "source": "serp_google_news",  # Add the source of the data
                }
            )
        logger.info(f"Sample response from Google News: {google_news_data[0]}")

    return google_news_data
