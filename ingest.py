import requests


def ingest(source):
    if source == "tia":
        return ingest_tia()
    else:
        raise ValueError("Unsupported source")


def ingest_tia():
    metadata = fetch_metadata()
    total_pages = metadata["total_pages"]
    per_page = metadata["per_page"]
    batch_size = 30  # Default batch size for TIA

    batches = generate_batches(total_pages, per_page, batch_size)
    for batch in batches:
        process_batch(batch)


def fetch_metadata():
    response = requests.get(
        "https://www.techinasia.com/wp-json/techinasia/2.0/posts?page=1"
    )
    return response.json()


def generate_batches(total_pages, per_page, batch_size, limit=None):
    if limit is None:
        limit = total_pages
    batches = []
    for i in range(0, min(limit, total_pages), batch_size):
        batch = list(range(i + 1, min(i + batch_size + 1, total_pages + 1)))
        batches.append(batch)
    return batches


def process_batch(batch):
    for page in batch:
        data = fetch_page_data(page)
        save_to_database(data)


def fetch_page_data(page):
    response = requests.get(
        f"https://www.techinasia.com/wp-json/techinasia/2.0/posts?page={page}"
    )
    return response.json()


def save_to_database(data):
    # Implement database save logic here
    pass
