import pytest
from fastapi.testclient import TestClient
from raggaeton.backend.src.api.endpoints.main import app
from raggaeton.backend.src.schemas.research import (
    GenerateResearchQuestionsRequest,
    DoResearchRequest,
)

client = TestClient(app)


@pytest.fixture
def generate_research_questions_payload():
    return {
        "topics": ["Health & Wellbeing", "Technology Trends"],
        "article_types": ["how-to", "benefits"],
        "platforms": ["you.com"],
        "optional_params": {
            "personas": [
                "general audience"
            ],  # This can now be a string or list of strings
            "country": "US",
        },
    }


@pytest.fixture
def do_research_payload():
    return {
        "research_questions": [
            {
                "platform": "you.com",  # This can now be a string or list of strings
                "keywords": ["health", "wellbeing"],
            },
        ],
        "optional_params": {"desired_length": 5},
    }


def test_generate_research_questions(generate_research_questions_payload):
    GenerateResearchQuestionsRequest(**generate_research_questions_payload)
    response = client.post(
        "/api/generate-research-questions", json=generate_research_questions_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert "research_questions" in data
    assert "token_count" in data


def test_do_research(do_research_payload):
    DoResearchRequest(**do_research_payload)
    response = client.post("/api/do-research", json=do_research_payload)
    assert response.status_code == 200
    data = response.json()
    assert "fetched_research" in data
    assert "token_count" in data
