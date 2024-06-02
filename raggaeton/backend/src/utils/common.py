import os
import yaml
from dotenv import load_dotenv


def find_project_root(current_path):
    """Traverse up until we find pyproject.toml, indicating the project root."""
    while True:
        if os.path.exists(os.path.join(current_path, "pyproject.toml")):
            return current_path
        parent = os.path.dirname(current_path)
        if parent == current_path:  # Reached the root directory
            break
        current_path = parent
    raise FileNotFoundError(
        "Could not find pyproject.toml. Are you sure this is the right directory?"
    )


# Determine the base directory by finding the project root
try:
    base_dir = find_project_root(os.path.dirname(__file__))
except FileNotFoundError:
    # Fallback to a default path if pyproject.toml is not found
    base_dir = (
        "/root/raggaeton"  # Adjust this path as needed for your remote environment
    )

# Print the base directory for verification
print(f"Base directory: {base_dir}")

# Load environment variables
dotenv_path = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path=dotenv_path)


def load_config():
    """Load configuration from config.yaml located in the config directory under the package."""
    config_path = os.path.join(os.path.dirname(__file__), "../config", "config.yaml")
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


class ConfigLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        self._load_env()
        self._load_yaml_config()
        self._load_prompts()

    def _load_env(self):
        dotenv_path = os.path.join(base_dir, ".env")
        load_dotenv(dotenv_path=dotenv_path)
        self.secrets = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "CLAUDE_API_KEY": os.getenv("CLAUDE_API_KEY"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "GOOGLE_SEARCH_ENGINE_ID": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
            "SUPABASE_PW": os.getenv("SUPABASE_PW"),
            # Add other secrets here
        }

    def _load_yaml_config(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "../config", "config.yaml"
        )
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)

    def _load_prompts(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../config", "prompts.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as file:
                self.prompts = file.read()
        else:
            self.prompts = ""

    def get_config(self):
        return self.config

    def get_secret(self, key):
        return self.secrets.get(key)

    def get_prompts(self):
        return self.prompts


# Initialize the ConfigLoader once so it can be used globally
config_loader = ConfigLoader()
