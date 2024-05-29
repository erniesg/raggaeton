import pytest
from raggaeton.backend.src.db.supabase import (
    insert_data,
    fetch_data,
    delete_data,
    update_data,
)
from raggaeton.backend.src.utils.common import load_config

# Load configuration
config = load_config()
test_table = config.get("test_table")


@pytest.fixture(scope="module")
def setup_supabase():
    from raggaeton.backend.src.db.supabase import supabase

    return supabase


def test_insert_and_fetch_data():
    # Insert data
    insert_data(test_table, {"title": "Test Post", "content": "This is a test"})

    # Fetch data
    fetched_data = fetch_data(test_table, filters=[("eq", "title", "Test Post")])
    assert len(fetched_data) == 1, "Data was not inserted or fetched properly."
    assert (
        fetched_data[0]["content"] == "This is a test"
    ), "Fetched content does not match inserted content."

    # Cleanup
    delete_data(test_table, {"title": "Test Post"})


def test_update_data():
    # Setup
    insert_data(test_table, {"title": "Update Test", "content": "Before update"})

    # Update data
    update_data(
        test_table,
        {"title": "Update Test"},
        {"content": "After update"},
    )

    # Verify update
    updated_data = fetch_data(test_table, filters=[("eq", "title", "Update Test")])
    assert len(updated_data) == 1, "Data was not updated or fetched properly."
    assert (
        updated_data[0]["content"] == "After update"
    ), "Updated content does not match expected content."

    # Cleanup
    delete_data(test_table, {"title": "Update Test"})
