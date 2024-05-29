import unittest
import logging
from unittest.mock import patch, MagicMock
from raggaeton.backend.src.api.endpoints.ingest import (
    fetch_metadata,
    generate_batches,
    process_batch,
)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TestIngestionProcess(unittest.TestCase):
    @patch("raggaeton.backend.src.api.endpoints.ingest.requests.get")
    def test_fetch_metadata(self, mock_get):
        # Mock the API response
        mock_get.return_value.json.return_value = {
            "total": 52983,
            "per_page": 30,
            "current_page": 20,
            "total_pages": 1767,
        }
        metadata = fetch_metadata()
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
    @patch("raggaeton.backend.src.api.endpoints.ingest.fetch_page_data")
    def test_process_batch(
        self, mock_fetch_page_data, mock_save_to_database, mock_log_status
    ):
        # Setup mock responses
        mock_fetch_page_data.return_value = {"id": "842575", "title": "Sample Post"}
        mock_save_to_database.return_value = None
        mock_log_status.return_value = None

        supabase_client = MagicMock()  # Mock the Supabase client
        batch_number = 1
        batch = [1, 2, 3]  # Example batch of 3 pages

        # Execute the function
        process_batch(supabase_client, batch_number, batch)

        # Assertions to check if fetch_page_data was called correctly
        self.assertEqual(mock_fetch_page_data.call_count, 3)
        mock_fetch_page_data.assert_has_calls(
            [
                patch(
                    "raggaeton.backend.src.api.endpoints.ingest.fetch_page_data",
                    args=(1,),
                ),
                patch(
                    "raggaeton.backend.src.api.endpoints.ingest.fetch_page_data",
                    args=(2,),
                ),
                patch(
                    "raggaeton.backend.src.api.endpoints.ingest.fetch_page_data",
                    args=(3,),
                ),
            ]
        )

        # Assertions to check if save_to_database was called correctly
        self.assertEqual(mock_save_to_database.call_count, 3)

        # Assertions to check if log_status was called correctly
        self.assertEqual(mock_log_status.call_count, 3)
        mock_log_status.assert_has_calls(
            [
                patch(
                    "raggaeton.backend.src.api.endpoints.ingest.log_status",
                    args=(supabase_client, batch_number, 1, "done"),
                ),
                patch(
                    "raggaeton.backend.src.api.endpoints.ingest.log_status",
                    args=(supabase_client, batch_number, 2, "done"),
                ),
                patch(
                    "raggaeton.backend.src.api.endpoints.ingest.log_status",
                    args=(supabase_client, batch_number, 3, "done"),
                ),
            ]
        )


if __name__ == "__main__":
    unittest.main()
