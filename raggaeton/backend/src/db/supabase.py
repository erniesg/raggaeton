from supabase import create_client
from raggaeton.backend.src.utils.common import config_loader
from raggaeton.backend.src.utils.error_handler import ConfigurationError
import logging

logger = logging.getLogger(__name__)

# Ensure the configuration and secrets are loaded
config = config_loader.get_config()
secrets = config_loader.secrets
logger.debug(f"Config keys: {list(config.keys())}")
logger.debug(f"Secrets keys: {list(secrets.keys())}")

SUPABASE_URL = config.get("table_url")
SUPABASE_KEY = secrets.get("SUPABASE_KEY")
logger.debug(f"SUPABASE_URL: {SUPABASE_URL[:8]}... (truncated)")
logger.debug(f"SUPABASE_KEY: {SUPABASE_KEY[:8]}... (truncated)")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ConfigurationError("SUPABASE_URL and SUPABASE_KEY are required")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def insert_data(table_name, data):
    try:
        response = supabase.table(table_name).insert(data).execute()
        return response.data
    except Exception as e:
        logger.error(
            f"Exception during insert: {e}, Status Code: {response.status_code if response else 'No Response'}, Response: {response if response else 'No Response'}"
        )
        raise


def fetch_data(table_name, select_columns="*", filters=None, limit=None):
    query = supabase.table(table_name).select(select_columns)

    if filters:
        for filter_condition in filters:
            method, *args = filter_condition
            query = getattr(query, method)(*args)

    if limit:
        query = query.limit(limit)

    response = query.execute()
    return response.data


def update_data(table_name, match_criteria, new_data):
    query = supabase.table(table_name).update(new_data)
    for key, value in match_criteria.items():
        query = query.eq(key, value)
    response = query.execute()
    return response.data


def delete_data(table_name, match_criteria):
    query = supabase.table(table_name).delete()
    for key, value in match_criteria.items():
        query = query.eq(key, value)
    response = query.execute()
    return response.data


def upsert_data(table_name, data):
    response = None  # Initialize response to None

    try:
        response = supabase.table(table_name).upsert(data).execute()
        return response.data
    except Exception as e:
        logger.error(
            f"Exception during upsert: {e}, Status Code: {getattr(response, 'status_code', 'No Response')}, Response: {getattr(response, 'data', 'No Response')}"
        )
        raise
