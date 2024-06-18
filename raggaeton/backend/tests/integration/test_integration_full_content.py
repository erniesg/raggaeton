import pytest
from fastapi.testclient import TestClient
from raggaeton.backend.src.api.endpoints.main import app
import json

client = TestClient(app)


@pytest.fixture
def sample_request():
    return {
        "headline": "How Remote Work Boosts Employee Productivity at TechCorp",
        "hook": "Discover the surprising benefits of remote work.",
        "thesis": "Remote work has significantly increased employee productivity and job satisfaction at TechCorp.",
        "article_type": "benefits",
        "draft_outlines": [
            {
                "content_block": "Introduction",
                "details": "Introduction to the benefits of remote work.",
                "topic_sentences": [
                    "Remote work has transformed the traditional workplace environment, offering numerous benefits for both employees and employers.",
                    "At TechCorp, the shift to remote work has revealed unexpected advantages, significantly boosting productivity and job satisfaction.",
                ],
            },
            {
                "content_block": "Overview",
                "details": "Overview of how remote work impacts productivity.",
                "topic_sentences": [
                    "Remote work has been shown to enhance employee productivity by creating a flexible and comfortable work environment.",
                    "TechCorp's implementation of remote work policies has resulted in measurable increases in employee output and overall efficiency.",
                ],
            },
        ],
        "optional_params": {
            "data": "case studies",
            "publication": "Forbes",
            "country": "Canada",
            "personas": ["managers", "remote workers"],
            "desired_length": 2000,
            "scratchpad": "Remote work has increased productivity and job satisfaction",
        },
    }


def test_generate_full_content(sample_request):
    response = client.post("/api/generate-full-content", json=sample_request)

    # Debugging: Print request and response details
    print("Request Payload:", json.dumps(sample_request, indent=2))
    print("Response Status Code:", response.status_code)
    print("Response Content:", response.json())

    assert response.status_code == 200
    assert "full_content" in response.json()
    assert len(response.json()["full_content"]) == len(sample_request["draft_outlines"])

    # Print the full response for visibility
    print(response.json())
