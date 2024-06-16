import unittest
import random
from raggaeton.backend.src.api.endpoints.ingest import ingest
from raggaeton.backend.src.db.supabase import fetch_data, delete_data
from raggaeton.backend.src.utils.common import load_config


class TestIntegrationIngest(unittest.TestCase):
    def setUp(self):
        # Load configuration and table names
        config = load_config()
        self.table_posts = config["table_posts"]
        self.table_batch_log = config["table_batch_log"]
        self.table_page_status = config["table_page_status"]

    def fetch_random_entry(self, table_name):
        data = fetch_data(table_name)
        if data:
            return random.choice(data)
        return None

    def test_ingest_tia(self):
        try:
            # Run the ingestion process
            ingest("tia", limit=2)

            # Fetch data from Supabase to verify ingestion
            posts = fetch_data(self.table_posts)
            batch_logs = fetch_data(self.table_batch_log)
            page_statuses = fetch_data(self.table_page_status)

            # Print the results for verification
            print(f"Number of posts ingested: {len(posts)}")
            print(f"Batch logs: {batch_logs[:1]}")  # Print a sample entry
            print(f"Page statuses: {page_statuses[:1]}")  # Print a sample entry

            # Fetch a random entry from each table
            random_post = self.fetch_random_entry(self.table_posts)
            random_batch_log = self.fetch_random_entry(self.table_batch_log)
            random_page_status = self.fetch_random_entry(self.table_page_status)

            # Print the random entries for verification
            print(f"Random post: {random_post}")
            print(f"Random batch log: {random_batch_log}")
            print(f"Random page status: {random_page_status}")

            # Assertions to verify the ingestion process
            self.assertGreater(len(posts), 0, "No posts were ingested.")
            self.assertGreater(len(batch_logs), 0, "No batch logs were created.")
            self.assertGreater(len(page_statuses), 0, "No page statuses were created.")

            # Stronger assertions
            self.assertTrue(
                all("id" in post for post in posts), "Some posts are missing 'id'."
            )
            self.assertTrue(
                all("status" in log for log in batch_logs),
                "Some batch logs are missing 'status'.",
            )
            self.assertTrue(
                all("status" in status for status in page_statuses),
                "Some page statuses are missing 'status'.",
            )

            # Additional assertions for table lengths
            self.assertEqual(len(posts), 60, "Expected 60 posts to be ingested.")
            self.assertEqual(len(batch_logs), 1, "Expected 1 batch log to be created.")
            self.assertEqual(
                len(page_statuses), 2, "Expected 2 page statuses to be created."
            )

        except Exception as e:
            # Log the exception message without cluttering the console with traceback
            self.fail(f"Test failed with exception: {e}")

    def tearDown(self):
        # Clean up the tables with a WHERE clause to avoid APIError
        delete_data(self.table_posts, {"batch_number": 1})
        delete_data(self.table_batch_log, {"batch_number": 1})
        delete_data(self.table_page_status, {"batch_number": 1})


if __name__ == "__main__":
    unittest.main()
