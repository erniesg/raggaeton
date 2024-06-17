import os
import yaml
import logging
from dotenv import load_dotenv
from google.cloud import secretmanager
import logging.config
from raggaeton.backend.src.utils.error_handler import error_handling_context

logger = logging.getLogger(__name__)


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


try:
    base_dir = find_project_root(os.path.dirname(__file__))
except FileNotFoundError:
    base_dir = "/root/raggaeton"  # Adjust this fallback path as needed for remote env

# logger = logging.getLogger(__name__)
logger.info(f"Base directory: {base_dir}")


def load_config():
    """Load configuration from config.yaml located in the config directory under the package."""
    config_path = os.path.join(os.path.dirname(__file__), "../config", "config.yaml")
    logger.debug(f"Loading config from: {config_path}")
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    logger.debug(f"Config loaded: {config}")
    return config


class ConfigLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance.secrets = {}
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        logger.debug("Starting _load_config")

        with error_handling_context():
            self._load_env()
            self._load_yaml_config()
            self._load_prompts()
            self._setup_logging()
        logger.debug("Finished _load_config")

    def _load_env(self):
        with error_handling_context():
            # Look for .env file in the local project directory
            local_dotenv_path = os.path.join(base_dir, ".env")

            if os.path.exists(local_dotenv_path):
                load_dotenv(dotenv_path=local_dotenv_path)
                logger.info(f"Loaded .env file from {local_dotenv_path}")
            else:
                raise FileNotFoundError(
                    "Could not find .env file in the project directory."
                )

            # Log all environment variables to debug
            for key, value in os.environ.items():
                logger.debug(f"ENV {key}: {value}")

            gcp_credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
            logger.info(f"GCP_CREDENTIALS_PATH from .env: {gcp_credentials_path}")
            container_gcp_credentials_path = "/app/gcp-credentials.json"

            if gcp_credentials_path:
                logger.info(f"Checking existence of {gcp_credentials_path}")
                if os.path.exists(gcp_credentials_path):
                    logger.info(f"Found GCP credentials at {gcp_credentials_path}")
                    if os.access(gcp_credentials_path, os.R_OK):
                        logger.info("GCP credentials file is readable")
                        self._load_gcp_secrets(gcp_credentials_path)
                    else:
                        logger.error("GCP credentials file is not readable")
                elif os.path.exists(container_gcp_credentials_path):
                    logger.info(
                        "GCP credentials path provided. Attempting to load secrets from GCP Secret Manager."
                    )
                    self._load_gcp_secrets(container_gcp_credentials_path)
                else:
                    # If the specified path doesn't exist, try the mounted path inside the container
                    container_gcp_credentials_path = os.path.join(
                        "/app/keys", os.path.basename(gcp_credentials_path)
                    )
                    if os.path.exists(container_gcp_credentials_path):
                        logger.info(
                            "GCP credentials file not found at the specified path. Attempting to load from the mounted path inside the container."
                        )
                        self._load_gcp_secrets(container_gcp_credentials_path)
                    else:
                        raise FileNotFoundError(
                            f"GCP credentials file not found at {gcp_credentials_path} or {container_gcp_credentials_path}"
                        )
            else:
                logger.info(
                    "No GCP credentials path provided in .env. Loading secrets from .env file."
                )
                self.secrets = {
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                    "CLAUDE_API_KEY": os.getenv("CLAUDE_API_KEY"),
                    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
                    "GOOGLE_SEARCH_ENGINE_ID": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
                    "SUPABASE_PW": os.getenv("SUPABASE_PW"),
                    "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
                    "YDC_API_KEY": os.getenv("YDC_API_KEY"),
                    "REDDIT_CLIENT_ID": os.getenv("REDDIT_CLIENT_ID"),
                    "REDDIT_SECRET": os.getenv("REDDIT_SECRET"),
                    "SERP_API_KEY": os.getenv("SERP_API_KEY"),
                    "MODAL_API_KEY": os.getenv("MODAL_API_KEY"),
                    "JINA_READER_API": os.getenv("JINA_READER_API"),
                    # Add other secrets here
                }
                logger.info("Loaded secrets from .env file.")

    def _load_gcp_secrets(self, credentials_path):
        with error_handling_context():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GCP_PROJECT_ID")
            secret_names = [
                "OPENAI_API_KEY",
                "CLAUDE_API_KEY",
                "GOOGLE_API_KEY",
                "GOOGLE_SEARCH_ENGINE_ID",
                "SUPABASE_PW",
                "SUPABASE_KEY",
                "YDC_API_KEY",
                "REDDIT_CLIENT_ID",
                "REDDIT_SECRET",
                "SERP_API_KEY",
                "MODAL_API_KEY",
                "JINA_READER_API",
            ]
            self.secrets = {}
            for secret_name in secret_names:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                logger.info(f"Attempting to load secret: {name}")
                response = client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode("UTF-8")
                self.secrets[secret_name] = secret_value
                os.environ[secret_name] = secret_value  # Set the environment variable
            logger.info("Successfully loaded secrets from GCP Secret Manager.")

    def _load_yaml_config(self):
        logger.debug("Starting _load_yaml_config")

        config_path = os.path.join(
            os.path.dirname(__file__), "../config", "config.yaml"
        )
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)
        logger.debug(f"Config loaded: {self.config}")
        logger.debug("Finished _load_yaml_config")

    def _load_prompts(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "../config", "prompts.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as file:
                self.prompts = file.read()
        else:
            self.prompts = ""

    def _setup_logging(self):
        logger.debug("Starting _setup_logging")
        environment = os.getenv("ENVIRONMENT", "prod")
        logging_config = self.config.get("logging", {}).get(environment, {})
        log_level = logging_config.get("level", "INFO").upper()
        log_file = logging_config.get("file", "")
        enable_console = logging_config.get("enable_console", True)

        log_level = getattr(logging, log_level, logging.INFO)

        handlers = {}
        if log_file:
            log_file = os.path.join(base_dir, log_file)
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_file,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 3,
                "formatter": "default",
            }
        if enable_console:
            handlers["console"] = {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }

        logging_config_dict = {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                },
            },
            "handlers": handlers,
            "root": {
                "level": log_level,
                "handlers": list(handlers.keys()),
            },
        }

        logging.config.dictConfig(logging_config_dict)
        logger.debug("Logging configuration applied successfully")
        logger.debug("Finished _setup_logging")

    def get_config(self):
        return self.config

    def get_secret(self, key):
        return self.secrets.get(key)

    def get_prompts(self):
        return self.prompts


config_loader = ConfigLoader()
