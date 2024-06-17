import pytest
from fastapi.testclient import TestClient
from raggaeton.backend.src.api.endpoints.main import app
from raggaeton.backend.src.schemas.content import GenerateDraftRequest

client = TestClient(app)


@pytest.fixture
def generate_draft_payload_without_optional_params():
    return {
        "headline": "How Remote Work Boosts Employee Productivity at TechCorp",
        "hook": "Discover the surprising benefits of remote work.",
        "thesis": "Remote work has significantly increased employee productivity and job satisfaction at TechCorp.",
        "article_type": "benefits",
        "topics": "Remote Work, Productivity, TechCorp",
    }


@pytest.fixture
def generate_draft_payload_with_optional_params():
    return {
        "headline": "How Remote Work Boosts Employee Productivity at TechCorp",
        "hook": "Discover the surprising benefits of remote work.",
        "thesis": "Remote work has significantly increased employee productivity and job satisfaction at TechCorp.",
        "article_type": "benefits",
        "topics": "Remote Work, Productivity, TechCorp",
        "optional_params": {
            "desired_length": 1500,
            "data": "survey results",
            "publication": "Tech in Asia",
            "country": "USA",
            "personas": ["HR managers", "employees"],
            "scratchpad": "Remote work has increased productivity",
        },
    }


def test_generate_draft_without_optional_params(
    generate_draft_payload_without_optional_params,
):
    # Construct the request
    request = GenerateDraftRequest(**generate_draft_payload_without_optional_params)

    # Log the constructed request
    print(f"Constructed Request (without optional params): {request.model_dump_json()}")

    # Make the API call
    response = client.post(
        "/api/generate-draft", json=generate_draft_payload_without_optional_params
    )
    data = response.json()

    # Print the type and content of the response for debugging
    print(f"Response type: {type(data)}")
    print(f"Response content: {data}")

    # Assert the response
    assert response.status_code == 200

    assert "drafts" in data
    assert len(data["drafts"]) > 0
    for draft in data["drafts"]:
        assert "headline" in draft
        assert "hook" in draft
        assert "thesis" in draft
        assert "article_type" in draft
        assert "structure" in draft
        assert len(draft["structure"]) > 0
        for block in draft["structure"]:
            assert "content_block" in block
            assert "details" in block


def test_generate_draft_with_optional_params(
    generate_draft_payload_with_optional_params,
):
    # Construct the request
    request = GenerateDraftRequest(**generate_draft_payload_with_optional_params)

    # Log the constructed request
    print(f"Constructed Request (with optional params): {request.model_dump_json()}")

    # Make the API call
    response = client.post(
        "/api/generate-draft", json=generate_draft_payload_with_optional_params
    )
    data = response.json()

    # Print the type and content of the response for debugging
    print(f"Response type: {type(data)}")
    print(f"Response content: {data}")
    # Assert the response
    assert response.status_code == 200

    assert "drafts" in data
    assert len(data["drafts"]) > 0
    for draft in data["drafts"]:
        assert "headline" in draft
        assert "hook" in draft
        assert "thesis" in draft
        assert "article_type" in draft
        assert "structure"
