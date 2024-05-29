import unittest
import logging
from unittest.mock import patch, call
from raggaeton.backend.src.api.endpoints.ingest import (
    fetch_metadata,
    generate_batches,
    process_batch,
)
from raggaeton.backend.src.utils.common import load_config

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

config = load_config()
TABLE_POSTS = config["table_posts"]
TABLE_BATCH_LOG = config["table_batch_log"]
TABLE_PAGE_STATUS = config["table_page_status"]


class TestIngestionProcess(unittest.TestCase):
    @patch("raggaeton.backend.src.api.endpoints.ingest.requests.get")
    def test_fetch_metadata(self, mock_get):
        # Mock the API response
        mock_get.return_value.json.return_value = {
            "total": 52983,
            "per_page": 30,
            "current_page": 20,
            "total_pages": 1767,
            "posts": [],  # Ensure 'posts' key is present
        }
        metadata = fetch_metadata(page=1)  # Provide the required page argument
        self.assertEqual(metadata["total_pages"], 1767)
        self.assertEqual(metadata["per_page"], 30)

    def test_generate_batches(self):
        total_pages = 1767
        batch_size = 30
        batches = generate_batches(total_pages, batch_size)
        self.assertEqual(len(batches), 59)  # 1767 pages / 30 pages per batch
        self.assertTrue(
            all(len(batch) == 30 for batch in batches[:-1])
        )  # All but last batch should have 30 pages
        self.assertTrue(len(batches[-1]) <= 30)  # Last batch should have <= 30 pages

    @patch("raggaeton.backend.src.api.endpoints.ingest.log_status")
    @patch("raggaeton.backend.src.api.endpoints.ingest.save_to_database")
    @patch("raggaeton.backend.src.api.endpoints.ingest.fetch_metadata")
    def test_process_batch(
        self, mock_fetch_metadata, mock_save_to_database, mock_log_status
    ):
        # Setup mock responses
        mock_fetch_metadata.return_value = {
            "posts": [
                {
                    "id": "842575",
                    "title": "Sample Post",
                    "content": "Content",
                    "date_gmt": "2023-01-01T00:00:00",
                    "modified_gmt": "2023-01-01T00:00:00",
                    "link": "http://example.com",
                    "status": "published",
                    "excerpt": "Sample excerpt",
                    "author": {
                        "id": "123",
                        "first_name": "John",
                        "last_name": "Doe",
                    },
                    "editor": "Editor Name",
                    "comments_count": 5,
                }
            ]
        }
        mock_save_to_database.return_value = None
        mock_log_status.return_value = None

        batch_number = 1
        batch = [1, 2, 3]  # Example batch of 3 pages

        # Execute the function
        process_batch(batch_number, batch)

        # Assertions to check if fetch_page_data was called correctly
        self.assertEqual(mock_fetch_metadata.call_count, 3)
        mock_fetch_metadata.assert_has_calls([call(1), call(2), call(3)])

        # Assertions to check if save_to_database was called correctly
        print(
            f"save_to_database call count: {mock_save_to_database.call_count}"
        )  # Debugging line
        self.assertEqual(mock_save_to_database.call_count, 3)

        # Assertions to check if log_status was called correctly
        self.assertEqual(mock_log_status.call_count, 3)
        mock_log_status.assert_has_calls(
            [
                call(batch_number, 1, "done"),
                call(batch_number, 2, "done"),
                call(batch_number, 3, "done"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
