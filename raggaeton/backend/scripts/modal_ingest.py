import os
import sys
import logging
import modal
import requests
import time

logger = logging.getLogger(__name__)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

ingest_image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "requests", "supabase", "PyYAML", "python-dotenv"
)

app = modal.App(name="tia-ingest-app", image=ingest_image)

raggaeton_mount = modal.Mount.from_local_dir(
    local_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
    remote_path="/app/raggaeton",
    condition=lambda pth: not pth.endswith(".env")
    and not pth.endswith("modal_ingest.py"),
    recursive=True,
)


@app.local_entrypoint()
def main():
    from raggaeton.backend.src.utils.common import load_config

    logger.info("Starting the ingestion process")

    config = load_config()
    env_vars = {
        "SUPABASE_URL": config["table_url"],
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
        "TABLE_POSTS": config["table_posts"],
        "TABLE_BATCH_LOG": config["table_batch_log"],
        "TABLE_PAGE_STATUS": config["table_page_status"],
    }

    total_pages = 100
    batch_size = 10

    for start_page in range(1, total_pages + 1, batch_size):
        batch_args = [
            (page, env_vars) for page in range(start_page, start_page + batch_size)
        ]

        try:
            list(fetch_and_process_page.starmap(batch_args))
        except Exception as e:
            logger.error(f"Error processing batch starting at page {start_page}: {e}")


@app.function(mounts=[raggaeton_mount])
def fetch_and_process_page(page, env_vars):
    sys.path.insert(0, "/app/raggaeton")
    logger.info(f"Current working directory: {os.getcwd()}")

    os.environ.update(env_vars)

    from raggaeton.backend.src.api.endpoints.ingest import (
        extract_relevant_data,
        save_to_database,
        log_status,
    )

    try:
        page_data = fetch_metadata_remote.remote(page)
        posts = extract_relevant_data(page_data)
        if posts:
            save_to_database(posts, 1, page)
            log_status(1, page, "done")
            logger.info(f"Completed processing page {page}")
    except Exception as e:
        log_status(1, page, f"error: {str(e)}")
        logger.error(f"Error processing page {page}: {e}")


@app.function(mounts=[raggaeton_mount])
def fetch_metadata_remote(page):
    sys.path.insert(0, "/app/raggaeton")
    from raggaeton.backend.src.utils.common import base_dir

    cookie_path = os.path.join(base_dir, "raggaeton/backend/src/config/tia_cookie.txt")

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

    max_retries = 5
    backoff_factor = 1

    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"https://www.techinasia.com/wp-json/techinasia/2.0/posts?page={page}",
                headers=headers,
            )
            response.raise_for_status()
            response_json = response.json()

            if "current_page" not in response_json:
                logging.error(f"Missing 'current_page' in response: {response_json}")
                raise KeyError("'current_page' not found in response")

            logging.info(
                f"Fetched page {response_json['current_page']} with {len(response_json['posts'])} posts."
            )

            if "set-cookie" in response.headers:
                new_cookie = response.headers["set-cookie"]
                with open(cookie_path, "w") as file:
                    file.write(new_cookie)
                headers["Cookie"] = new_cookie

            return response_json
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            logging.error(f"Response content: {e.response.content}")
            logging.error(f"Response headers: {e.response.headers}")
            if e.response.status_code == 429:
                sleep_time = backoff_factor * (2**attempt)
                logging.info(f"Rate limit hit. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            elif attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                logging.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                raise


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
