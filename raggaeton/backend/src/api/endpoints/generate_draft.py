import json
from fastapi import APIRouter
from raggaeton.backend.src.schemas.content import (
    GenerateDraftRequest,
    GenerateDraftResponse,
    ContentBlock,
    Draft,
)

router = APIRouter()


# Load the JSON configuration
def load_template(article_type):
    with open(f"config/article_templates/{article_type}.json") as f:
        return json.load(f)


def load_content_blocks():
    with open("config/article_templates/content_blocks.json") as f:
        return json.load(f)


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(request: GenerateDraftRequest):
    template = load_template(request.article_type)
    content_blocks = load_content_blocks()
    structures = template["structures"]

    # Select a structure (for simplicity, we select the first one)
    selected_structure = structures[0]

    # Generate the draft
    draft_structure = [
        ContentBlock(content_block=block, details=content_blocks[block]["details"])
        for block in selected_structure
    ]

    draft = Draft(headline=request.headline, structure=draft_structure)

    return GenerateDraftResponse(drafts=[draft])
