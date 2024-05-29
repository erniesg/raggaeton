import os
import yaml
from dotenv import load_dotenv


def find_project_root(current_path):
    """Traverse up until we find pyproject.toml, indicating the project root."""
    while not os.path.exists(os.path.join(current_path, "pyproject.toml")):
        parent = os.path.dirname(current_path)
        if parent == current_path:
            # We've reached the root of the filesystem without finding pyproject.toml
            raise FileNotFoundError(
                "Could not find pyproject.toml. Are you sure this is the right directory?"
            )
        current_path = parent
    return current_path


# Determine the base directory by finding the project root
base_dir = find_project_root(os.path.dirname(__file__))

# Load environment variables
dotenv_path = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path=dotenv_path)


def load_config():
    """Load configuration from config.yaml located in the config directory under the project root."""
    config_path = os.path.join(base_dir, "raggaeton/backend/src/config", "config.yaml")
    with open(config_path, "r") as file:
        return yaml.safe_load(file)
