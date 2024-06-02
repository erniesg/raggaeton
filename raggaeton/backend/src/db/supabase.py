import os
from supabase import create_client
from raggaeton.backend.src.utils.common import load_config
import logging

logger = logging.getLogger(__name__)
config = load_config()

SUPABASE_URL = config["table_url"]
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    response = supabase.table(table_name).upsert(data).execute()
    return response.data
