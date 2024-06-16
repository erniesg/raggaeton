import unittest
import logging
from raggaeton.backend.src.api.endpoints.ingest import ingest_research_data
from raggaeton.backend.src.db.supabase import fetch_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestIntegrationIngestBalance(unittest.TestCase):
    def test_ingest_research_data(self):
        topic = "Careers & Entrepreneurship"
        article_types = [
            "listicles",
            "strategies-and-case-studies",
        ]
        platforms = ["wikipedia"]
        personas = ["about to graduate arts major in brisbane", "working parent"]
        target_audience = "AU"
        limit = 2

        response = {}  # Initialize response with an empty dictionary

        try:
            response = ingest_research_data(
                topic, article_types, platforms, personas, target_audience, limit
            )
        except Exception as e:
            logger.error(f"Error during ingest_research_data: {e}")
            raise

        # Log the response
        logger.info(f"Response: {response}")

        # Log the number of items and a sample item for each platform
        for platform, data in response.items():
            num_items = len(data)
            logger.info(f"Platform: {platform}")
            logger.info(f"Number of items: {num_items}")
            if num_items > 0:
                sample_item = data[0]
                logger.info(f"Sample item: {sample_item}")
            logger.info("---")

        # Assertions to check if data was fetched for each platform
        self.assertIn("wikipedia", response)

        # Additional assertions to check if raw_content is not empty
        for platform, data in response.items():
            for item in data:
                self.assertNotEqual(
                    item["raw_content"], "", f"Empty raw_content for item in {platform}"
                )

    def test_data_saved_to_supabase(self):
        # Fetch data from Supabase to verify it was saved correctly
        table_name = "balancethegrind_fetched_data"
        fetched_data = fetch_data(table_name)

        # Log the fetched data
        logger.info(f"Fetched data from Supabase: {fetched_data}")

        # Assertions to check if the data was saved correctly
        self.assertGreater(len(fetched_data), 0, "No data found in Supabase")

        # Check if the required fields are present in the fetched data
        for record in fetched_data:
            self.assertIn("id", record)
            self.assertIn("title", record)
            self.assertIn("date_fetched", record)
            self.assertIn("created_at", record)
            self.assertIn("author", record)
            self.assertIn("raw_content", record)
            self.assertIn("url", record)


if __name__ == "__main__":
    unittest.main()
