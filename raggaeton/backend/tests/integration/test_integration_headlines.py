import pytest
from fastapi.testclient import TestClient
from raggaeton.backend.src.api.endpoints.main import app
from raggaeton.backend.src.schemas.content import GenerateHeadlinesRequest

client = TestClient(app)


@pytest.fixture
def generate_headlines_payload():
    return {
        "article_types": "benefits",
        "topics": ["remote work", "employee productivity"],
        "context": {"company": "TechCorp", "date_gmt": "2023-10-01"},
        "optional_params": {
            "data": "survey results",
            "publication": "Tech in Asia",
            "country": "USA",
            "personas": ["HR managers", "employees"],
            "desired_length": 5,
            "limit": 3,
            "scratchpad": "Remote work has increased productivity. Employees report higher job satisfaction.",
        },
    }


def test_generate_headlines(generate_headlines_payload):
    GenerateHeadlinesRequest(**generate_headlines_payload)
    response = client.post("/api/generate-headlines", json=generate_headlines_payload)
    assert response.status_code == 200
    data = response.json()

    # Print the type and content of the response for debugging
    print(f"Response type: {type(data)}")
    print(f"Response content: {data}")

    assert "headlines" in data
    assert len(data["headlines"]) > 0
    for headline in data["headlines"]:
        assert "headline" in headline
        assert "article_type" in headline
        assert "hook" in headline
        assert "thesis" in headline
