import pytest
from fastapi.testclient import TestClient
from raggaeton.backend.src.api.endpoints.main import (
    app,
)  # Adjust the import based on your project structure

client = TestClient(app)


@pytest.fixture
def base_request():
    return {
        "headline": "Life Lessons from Hiking and Gradient Descent",
        "hook": "Hiking is not just a physical activity; it's a journey that mirrors the ups and downs of life.",
        "thesis": "This experience taught me valuable life lessons that can be applied to both hiking and the concept of gradient descent in machine learning.",
        "article_type": "Benefits Article",
        "optional_params": {
            "personas": ["Hikers", "Machine Learning Enthusiasts"],
            "scratchpad": "I went hiking and saw an ant trying to move a flower on a hike. It was doing so with all its might.",
            "desired_length": 1000,
        },
        "draft_outlines": [
            {
                "content_block": "Introduction",
                "details": "Hook: Hiking is not just a physical activity; it's a journey that mirrors the ups and downs of life. Thesis Statement: This experience taught me valuable life lessons that can be applied to both hiking and the concept of gradient descent in machine learning.",
                "topic_sentences": [
                    "Hiking offers more than just physical benefits; it provides profound life lessons."
                ],
            },
            {
                "content_block": "Overview of the Topic",
                "details": "Summary of Key Points: Hiking and gradient descent both involve overcoming obstacles, persistence, and finding the right path.",
                "topic_sentences": [
                    "Both hiking and gradient descent require persistence and the ability to navigate challenges."
                ],
            },
            {
                "content_block": "Benefits",
                "details": "Benefit 1: Physical Health - Hiking improves cardiovascular health, strengthens muscles, and enhances mental well-being. Benefit 2: Mental Clarity - The challenges faced during a hike can clear the mind and provide a fresh perspective. Benefit 3: Life Lessons - Observing nature teaches persistence and problem-solving.",
                "topic_sentences": [
                    "Hiking offers numerous physical and mental benefits."
                ],
            },
            {
                "content_block": "Tips for Implementation",
                "details": "Tip 1: Start Small - Begin with easy trails and gradually increase the difficulty. Tip 2: Stay Consistent - Regular hiking builds endurance and resilience. Tip 3: Reflect and Learn - Take time to reflect on the experiences and lessons learned during each hike.",
                "topic_sentences": [
                    "Implementing these tips can enhance your hiking experience."
                ],
            },
            {
                "content_block": "Conclusion",
                "details": "Restate Thesis: Hiking and gradient descent both teach us valuable life lessons about persistence and finding the right path. Reiterate Supporting Points: The physical and mental benefits of hiking, along with the life lessons learned, make it a rewarding activity. Clincher: So, lace up your hiking boots and embrace the journey, both on the trail and in life.",
                "topic_sentences": [
                    "In conclusion, hiking and gradient descent offer valuable life lessons."
                ],
            },
        ],
    }


@pytest.mark.parametrize("edit_type", ["edit_draft", "edit_flair"])
def test_edit_content(base_request, edit_type):
    base_request["edit_type"] = edit_type
    response = client.post("/api/edit-content", json={"request": base_request})
    assert response.status_code == 200, f"Response content: {response.content}"
    data = response.json()
    print(f"Response for {edit_type}: {data}")
    assert "edited_content" in data
    assert len(data["edited_content"]) > 0
    for content_block in data["edited_content"]:
        assert "content_block" in content_block
        assert "details" in content_block
        assert "topic_sentences" in content_block
        assert "paragraphs" in content_block
