import requests
from raggaeton.backend.src.db.supabase import supabase, upsert_data


def ingest(source):
    if source == "tia":
        return ingest_tia()
    else:
        raise ValueError("Unsupported source")


def ingest_tia():
    metadata = fetch_metadata()
    total_pages = metadata["total_pages"]
    batch_size = 30  # Default batch size for TIA

    batches = generate_batches(total_pages, batch_size)
    for batch_number, batch in enumerate(batches, start=1):
        log_batch_initiation(supabase, batch_number)
        process_batch(supabase, batch_number, batch)


def fetch_metadata():
    response = requests.get(
        "https://www.techinasia.com/wp-json/techinasia/2.0/posts?page=1"
    )
    return response.json()


def generate_batches(total_pages, batch_size, limit=None):
    if limit is None:
        limit = total_pages
    batches = []
    for i in range(0, min(limit, total_pages), batch_size):
        batch = list(range(i + 1, min(i + batch_size + 1, total_pages + 1)))
        batches.append(batch)
    return batches


def process_batch(supabase, batch_number, batch):
    for page_number in batch:
        try:
            page_data = fetch_page_data(page_number)
            posts = extract_relevant_data(page_data)
            if posts:
                save_to_database(supabase, posts, batch_number, page_number)
                log_status(supabase, batch_number, page_number, "done")
            else:
                log_status(supabase, batch_number, page_number, "no posts")
        except Exception as e:
            log_status(supabase, batch_number, page_number, f"error: {str(e)}")


def fetch_page_data(page):
    response = requests.get(
        f"https://www.techinasia.com/wp-json/techinasia/2.0/posts?page={page}"
    )
    return response.json()


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
    upsert_data(supabase, "posts", data)


def retry_processing(supabase):
    # Fetch all pages that are not marked as 'done'
    not_done_pages = (
        supabase.table("page_status").select("*").neq("status", "done").execute()
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
    supabase.table("batch_log").insert(
        {"batch_number": batch_number, "status": "started"}
    ).execute()


def log_status(supabase, batch_number, page_number, status):
    supabase.table("page_status").upsert(
        {"batch_number": batch_number, "page_number": page_number, "status": status}
    ).execute()
