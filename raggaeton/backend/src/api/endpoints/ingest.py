import requests
from raggaeton.backend.src.db.supabase import supabase, upsert_data
from raggaeton.backend.src.utils.common import load_config, base_dir
import os
import logging

config = load_config()
TABLE_POSTS = config["table_posts"]
TABLE_BATCH_LOG = config["table_batch_log"]
TABLE_PAGE_STATUS = config["table_page_status"]

logging.basicConfig(level=logging.INFO)


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
        log_batch_initiation(supabase, batch_number)
        process_batch(supabase, batch_number, batch)


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


def process_batch(supabase, batch_number, batch):
    for page_number in batch:
        try:
            page_data = fetch_metadata(page_number)  # Use fetch_metadata directly
            posts = extract_relevant_data(page_data)
            if posts:
                save_to_database(supabase, posts, batch_number, page_number)
                log_status(supabase, batch_number, page_number, "done")
            else:
                log_status(supabase, batch_number, page_number, "no posts")
        except Exception as e:
            log_status(supabase, batch_number, page_number, f"error: {str(e)}")


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
        }
        for post in page_data["posts"]
    ]


def save_to_database(supabase, posts, batch_number, page_number):
    data = [
        {"batch_number": batch_number, "page_number": page_number, **post}
        for post in posts
    ]
    upsert_data(supabase, TABLE_POSTS, data)


def retry_processing(supabase):
    # Fetch all pages that are not marked as 'done'
    not_done_pages = (
        supabase.table(TABLE_PAGE_STATUS).select("*").neq("status", "done").execute()
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
        process_batch(supabase, batch_number, pages)


def log_batch_initiation(supabase, batch_number):
    supabase.table(TABLE_BATCH_LOG).insert(
        {"batch_number": batch_number, "status": "started"}
    ).execute()


def log_status(supabase, batch_number, page_number, status):
    supabase.table(TABLE_PAGE_STATUS).upsert(
        {"batch_number": batch_number, "page_number": page_number, "status": status}
    ).execute()
