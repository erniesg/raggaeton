import pytest
from fastapi.testclient import TestClient
from raggaeton.backend.src.api.endpoints.main import app
from raggaeton.backend.src.schemas.content import GenerateTopicSentencesRequest

client = TestClient(app)


@pytest.fixture
def generate_topic_sentences_payload_without_optional_params():
    return {
        "headline": "How Remote Work Boosts Employee Productivity at TechCorp",
        "hook": "Discover the surprising benefits of remote work.",
        "thesis": "Remote work has significantly increased employee productivity and job satisfaction at TechCorp.",
        "article_type": "benefits",
        "structure": [
            {
                "content_block": "Introduction",
                "details": "Introduction to the benefits of remote work.",
            },
            {
                "content_block": "Overview",
                "details": "Overview of how remote work impacts productivity.",
            },
        ],
    }


@pytest.fixture
def generate_topic_sentences_payload_with_optional_params():
    return {
        "headline": "How Remote Work Boosts Employee Productivity at TechCorp",
        "hook": "Discover the surprising benefits of remote work.",
        "thesis": "Remote work has significantly increased employee productivity and job satisfaction at TechCorp.",
        "article_type": "benefits",
        "structure": [
            {
                "content_block": "Introduction",
                "details": "Introduction to the benefits of remote work.",
            },
            {
                "content_block": "Overview",
                "details": "Overview of how remote work impacts productivity.",
            },
        ],
        "optional_params": {
            "desired_length": 2000,
            "data": "case studies",
            "publication": "Forbes",
            "country": "Canada",
            "personas": ["managers", "remote workers"],
            "scratchpad": "Remote work has increased productivity and job satisfaction",
        },
    }


def test_generate_topic_sentences_without_optional_params(
    generate_topic_sentences_payload_without_optional_params,
):
    # Construct the request
    request = GenerateTopicSentencesRequest(
        **generate_topic_sentences_payload_without_optional_params
    )

    # Log the constructed request
    print(f"Constructed Request (without optional params): {request.model_dump_json()}")

    # Make the API call
    response = client.post(
        "/api/generate-topic-sentences",
        json=generate_topic_sentences_payload_without_optional_params,
    )
    data = response.json()

    # Print the type and content of the response for debugging
    print(f"Response type: {type(data)}")
    print(f"Response content: {data}")

    # Assert the response
    assert response.status_code == 200

    assert "draft_outlines" in data
    assert len(data["draft_outlines"]) > 0
    for outline in data["draft_outlines"]:
        assert "content_block" in outline
        assert "details" in outline
        assert "topic_sentences" in outline
        assert len(outline["topic_sentences"]) > 0


def test_generate_topic_sentences_with_optional_params(
    generate_topic_sentences_payload_with_optional_params,
):
    # Construct the request
    request = GenerateTopicSentencesRequest(
        **generate_topic_sentences_payload_with_optional_params
    )

    # Log the constructed request
    print(f"Constructed Request (with optional params): {request.model_dump_json()}")

    # Make the API call
    response = client.post(
        "/api/generate-topic-sentences",
        json=generate_topic_sentences_payload_with_optional_params,
    )
    data = response.json()

    # Print the type and content of the response for debugging
    print(f"Response type: {type(data)}")
    print(f"Response content: {data}")

    # Assert the response
    assert response.status_code == 200

    assert "draft_outlines" in data
    assert len(data["draft_outlines"]) > 0
    for outline in data["draft_outlines"]:
        assert "content_block" in outline
        assert "details" in outline
        assert "topic_sentences" in outline
        assert len(outline["topic_sentences"]) > 0
