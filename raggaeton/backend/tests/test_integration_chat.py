import unittest
import logging
from raggaeton.backend.src.api.endpoints.agent import create_agent
from raggaeton.backend.src.api.endpoints.tools import create_google_search_tool
from raggaeton.backend.src.utils.common import load_config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestAgentIntegration(unittest.TestCase):
    def setUp(self):
        # Load the configuration
        self.config = load_config()
        logger.debug(f"Loaded config: {self.config}")

        # Create the Google search tool
        self.google_search_tool = create_google_search_tool()
        logger.debug(f"Created Google search tool: {self.google_search_tool}")

        # List of tools to be used by the agent
        self.tools = [self.google_search_tool]
        logger.debug(f"Tools to be used by the agent: {self.tools}")

        # Extract model configuration
        self.model_config = self.config["llm"]["models"][0]
        self.model_name = self.model_config["model_name"]
        self.params = self.model_config["params"]
        self.api_key_env = self.model_config["api_key_env"]
        logger.debug(f"Model config: {self.model_config}")

    def test_create_openai_agent_with_tools(self):
        try:
            # Create an OpenAI agent with the Google search tool
            agent = create_agent("openai", self.tools, config=self.config, verbose=True)
            logger.debug(f"Created agent: {agent}")

            # Check if the agent is created successfully
            self.assertIsNotNone(agent)
            self.assertTrue(hasattr(agent, "chat"))
        except Exception as e:
            logger.error(f"Error in test_create_openai_agent_with_tools: {e}")
            raise

    def test_openai_agent_chat(self):
        try:
            # Create an OpenAI agent with the Google search tool
            agent = create_agent("openai", self.tools, verbose=True)
            logger.debug(f"Created agent: {agent}")

            # Send a query to the agent
            query = "What's trending today?"
            response = agent.chat(query)
            logger.debug(f"Query: {query}\nResponse: {response}")

            # Extract the actual response text
            response_text = (
                response.response if hasattr(response, "response") else response
            )
            logger.debug(f"Extracted response text: {response_text}")

            # Check if the response is valid
            self.assertIsNotNone(response_text)
            self.assertIsInstance(response_text, str)
        except Exception as e:
            logger.error(f"Error in test_openai_agent_chat: {e}")
            raise


if __name__ == "__main__":
    unittest.main()
