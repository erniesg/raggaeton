import requests
from datetime import datetime
import uuid
import os
from raggaeton.backend.src.utils.utils import truncate_log_message
from raggaeton.backend.src.utils.common import logger, error_handling_context
from llama_index.readers.obsidian import ObsidianReader


def fetch_data_from_you(keywords, limit=10, country="us", source="you_snippets"):
    with error_handling_context():
        api_key = os.getenv("YDC_API_KEY")
        headers = {"X-API-Key": api_key}

        if source == "you.com":
            url = "https://api.ydc-index.io/news"
            params = {"q": keywords, "count": limit, "country": country}
        else:
            url = "https://api.ydc-index.io/search"
            params = {"query": keywords, "count": limit, "country": country}

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
            raw_content = (
                " ".join(result.get("snippets", []))
                if source == "you_snippets"
                else result.get("description", "")
            )
            data.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": result.get("title"),
                    "date_fetched": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "author": result.get("author", "N/A"),
                    "raw_content": raw_content,
                    "url": result.get("url"),
                    "source": source,
                }
            )
        logger.info(
            f"Sample response from {source}: {truncate_log_message(str(data[0]))}"
        )
        return {"results": data}


def fetch_data_from_wikipedia(keywords, limit=10):
    with error_handling_context():
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
                page_url = (
                    f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                )
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
                logger.debug(f"Parsed data: {parse_data}")

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
                        "source": "wikipedia",
                    }
                )
                logger.info(
                    f"Appended data: {truncate_log_message(str(wikipedia_data[-1]))}"
                )
        return {"results": wikipedia_data}


def fetch_data_from_obsidian(vault_path, **kwargs):
    with error_handling_context():
        obsidian_reader = ObsidianReader(input_dir=vault_path)
        documents = obsidian_reader.load_data()

        obsidian_data = []
        for doc in documents:
            # Extract the first heading as the title if available
            title = "Untitled"
            for line in doc.text.splitlines():
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break

            obsidian_data.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "date_fetched": datetime.utcnow().isoformat(),
                    "created_at": kwargs.get(
                        "created_at", datetime.utcnow().isoformat()
                    ),
                    "author": kwargs.get("author", "N/A"),
                    "raw_content": doc.text,
                    "url": doc.metadata.get("source", "N/A"),
                    "source": "obsidian",
                }
            )
        logger.info(
            f"Sample response from Obsidian: {truncate_log_message(str(obsidian_data[0]))}"
        )
        return {"results": obsidian_data}
