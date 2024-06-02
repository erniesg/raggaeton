import os
import requests
from supabase import create_client
import logging
from raggaeton.backend.src.utils.common import load_config

config = load_config()
logger = logging.getLogger(__name__)
SUPABASE_URL = config["table_url"]
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MODAL_API_KEY = os.getenv("MODAL_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_html_content(limit=None):
    try:
        query = supabase.table(config["table_posts"]).select("id, content")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching data from Supabase: {e}")
        raise


def convert_html_to_markdown(html_content):
    """Convert HTML content to Markdown using the Modal API."""
    try:
        response = requests.post(
            "https://erniesg--clean-svc-clean.modal.run/",
            headers={"Authorization": f"Bearer {MODAL_API_KEY}"},
            json={"raw_content": html_content},
        )
        response.raise_for_status()
        return response.json()["cleaned_content"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error converting HTML to Markdown: {e}")
        raise


def update_markdown_content(record_id, markdown_content):
    try:
        supabase.table("tia_posts").update({"md_content": markdown_content}).eq(
            "id", record_id
        ).execute()
    except Exception as e:
        logger.error(f"Error updating Markdown content in Supabase: {e}")
        raise


def main(limit=None):
    logger.info("Starting content processing")

    # Fetch HTML content from Supabase
    records = fetch_html_content(limit)
    if not records:
        logger.info("No records found to process")
        return

    for record in records:
        record_id = record["id"]
        html_content = record["content"]

        logger.info(f"Processing record ID: {record_id}")
        logger.info(f"Original HTML content: {html_content}")

        # Convert HTML to Markdown
        try:
            markdown_content = convert_html_to_markdown(html_content)
            logger.info(f"Cleaned Markdown content: {markdown_content}")
            update_markdown_content(record_id, markdown_content)
            logger.info(f"Successfully processed record ID: {record_id}")
        except Exception as e:
            logger.error(f"Error processing record ID {record_id}: {e}")


if __name__ == "__main__":
    import sys

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit)
