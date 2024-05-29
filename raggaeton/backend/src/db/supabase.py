import os
from supabase import create_client
from raggaeton.backend.src.utils.common import load_config
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = load_config()

SUPABASE_URL = config["table_url"]
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize the Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def insert_data(supabase, table_name, data):
    try:
        response = supabase.table(table_name).insert(data).execute()
        logger.debug(f"Insert Success: {response}")
        return response.data
    except Exception as e:
        logger.error(
            f"Exception during insert: {e}, Status Code: {response.status_code if response else 'No Response'}, Response: {response if response else 'No Response'}"
        )
        raise


def fetch_data(supabase, table_name, select_columns="*", filters=None):
    query = supabase.table(table_name).select(select_columns)

    if filters:
        for filter_condition in filters:
            method, *args = filter_condition
            query = getattr(query, method)(*args)

    response = query.execute()
    return response.data


def update_data(supabase, table_name, match_criteria, new_data):
    query = supabase.table(table_name).update(new_data)
    for key, value in match_criteria.items():
        query = query.eq(key, value)
    response = query.execute()
    return response.data


def delete_data(supabase, table_name, match_criteria):
    query = supabase.table(table_name).delete()
    for key, value in match_criteria.items():
        query = query.eq(key, value)
    response = query.execute()
    return response.data
